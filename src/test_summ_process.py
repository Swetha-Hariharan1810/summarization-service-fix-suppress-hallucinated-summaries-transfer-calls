import json
import math
import multiprocessing
import os

import torch
from fairseq.data.encoders.gpt2_bpe import get_encoder
from fairseq.models.transformer import TransformerModel

from config import get_settings

ncpu = multiprocessing.cpu_count()
torch.set_num_threads(ncpu)

settings = get_settings()

bpe_path = "/home/ubuntu/codebase/data/gpt2_bpe/"

summarization_model_path = "/home/ubuntu/codebase/data/qa_detailed_summarizer_model_v0/"

if settings.GENERAL_SUMMARY:
    from sentence_transformers import SentenceTransformer

    sentence_similarity_model_path = (
        "/home/ubuntu/codebase/data/model/task_verification_model/"
    )
    reasons_path = "src/config/reasons.json"

    print("preloading sentence similarity model for general model only")
    sentence_understanding = SentenceTransformer(sentence_similarity_model_path)
    reasons = json.load(open(reasons_path))
    reasons_embedding = {
        k: [sentence_understanding.encode(vv) for vv in reasons[k]] for k in reasons
    }
    summary_exclusive = (
        "The customer needs to complete a customer service satisfaction survey"
    )
    summary_exclusive_embed = sentence_understanding.encode(summary_exclusive)
    print("preloading sentence similarity model for general model only done")

print("preloading summarization model")
bpe = get_encoder(
    os.path.join(bpe_path, "encoder.json"), os.path.join(bpe_path, "vocab.bpe")
)
summarizer = TransformerModel.from_pretrained(
    summarization_model_path,
    checkpoint_file="checkpoint.pt",
)
summarizer.eval()
summarizer = summarizer.to("cuda")
print("preloading summarization model done")


def process_summary(text, remove_lower_case=True, semantic_thredshold=0.9):
    early_stop = False
    text = [t.strip() for t in text.split(".") if t.strip()]
    text = [t + "." if t[-1] != "." else t for t in text]
    new_text = []
    for t in text:
        if t[0].isdigit() and len(new_text) > 0:
            new_text[-1] += t
        else:
            new_text.append(t)
    text = new_text
    if remove_lower_case:
        text = [t for t in text if t[0].upper() == t[0]]
    if semantic_thredshold < 1.0:
        text_embed = sentence_understanding.encode(text)
        final = []
        for idx, t in enumerate(text):
            if early_stop:
                continue
            if text_embed[idx].dot(summary_exclusive_embed) > semantic_thredshold:
                continue
            flag = False
            for j in final:
                if text_embed[idx].dot(text_embed[j]) > semantic_thredshold:
                    flag = True
                    break
            if not flag:
                final.append(idx)
            if "resolutions are" in t:
                early_stop = True
        final = set(final)
        text = [t for i, t in enumerate(text) if i in final]
    return " ".join(text)


def summarize(
    text_ip,
    questions,
    ratios,
    beam=4,
    no_repeat_ngram_size=3,
    temperature=0.5,
    semantic_thredshold=0.7,
    generate_reason=False,
    sliding_windows=False,
):
    # TODO: refactor
    concat_summary = []
    tokens_all = []
    truncate = False
    for q, r in zip(questions, ratios):
        # step 1 pre-append question
        if q:
            text = q + "\t" + text_ip
        else:
            text = text_ip

        # step 2 bpe, truncation, binary
        transcript_bpe = bpe.encode(text)
        if len(transcript_bpe) > summarizer.max_positions[0] - 2:
            if (
                len(transcript_bpe) < summarizer.max_positions[0] - 2 + 100
                or not sliding_windows
            ):
                transcript_bpes = [transcript_bpe[: summarizer.max_positions[0] - 2]]
            else:
                truncate = True
                # apply sliding window on long transcripts with 2k token overlapping.
                window_size = int(summarizer.max_positions[0] / 3 * 2)
                num_sliding_windows = len(transcript_bpe) // window_size
                transcript_bpes = [
                    transcript_bpe[
                        j * window_size : j * window_size
                        + summarizer.max_positions[0]
                        - 30
                    ]
                    for j in range(num_sliding_windows + 1)
                ]
                if q:
                    quenstion_encode = bpe.encode(q + "\t")
                else:
                    quenstion_encode = ""
                for j in range(1, len(transcript_bpes)):
                    transcript_bpes[j] = quenstion_encode + transcript_bpes[j]
        else:
            transcript_bpes = [transcript_bpe]
        minlen = max(5, math.ceil(r[0] * len(transcript_bpes[0])))
        maxlen = max(500, math.ceil(r[1] * len(transcript_bpes[0])))
        transcript_bpes = [
            " ".join([str(b) for b in transcript_bpe])
            for transcript_bpe in transcript_bpes
        ]
        transcript_bpes = [
            transcript_bpe + " </s>" for transcript_bpe in transcript_bpes
        ]
        tokens = [
            summarizer.task.source_dictionary.encode_line(
                transcript_bpe, append_eos=False
            )
            for transcript_bpe in transcript_bpes
        ]
        tokens_all.extend(tokens)

    # step 3 generate hypos
    with torch.no_grad():
        hypos = summarizer.generate(
            tokens_all,
            temperature=temperature,
            beam=beam,
            max_len_b=maxlen,
            min_len=minlen,
            no_repeat_ngram_size=no_repeat_ngram_size,
        )

    # step 4 convert back to bpe string and then convert back to words
    for hypo in hypos:
        candidate = summarizer.decode(hypo[0]["tokens"])
        best_summary = bpe.decode([int(b) for b in candidate.split(" ")]).strip()
        concat_summary.append(best_summary)

    # step 5 concat summaries
    concat_summary = " ".join(concat_summary)
    if sliding_windows and truncate and settings.GENERAL_SUMMARY:
        summary_processed = process_summary(
            concat_summary, semantic_thredshold=semantic_thredshold
        )
    else:
        # simple question doesn't have repeat
        summary_processed = concat_summary

    # step 6 generate classification
    best_reason = None
    if generate_reason and settings.GENERAL_SUMMARY:
        best_reason = ""
        best_reason_score = 0
        best_summary_embed_reasons = sentence_understanding.encode(summary_processed)
        for reason in reasons_embedding:
            reason_embed = reasons_embedding[reason]
            reason_score = max(
                [best_summary_embed_reasons.dot(v) for v in reason_embed]
            )
            if reason_score > best_reason_score:
                best_reason_score = reason_score
                best_reason = reason

    return concat_summary, summary_processed, best_reason
