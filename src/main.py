# import sys
# sys.path.append(".")

import datetime
import os
import time
import traceback
import uuid
from time import gmtime, strftime

# from src import mdt_stt_process_audio
import test_summ_process
from config import get_settings
from preprocess import word_to_digit
from preprocess.process_transcripts import (
    aggregate_by_channel,
    clean_transcript,
    get_symbol_to_word,
)
from summ_service import s3_util

settings = get_settings()

w2d_obj = word_to_digit.get_word_to_digit()
ARCHIEVE_DIR = "/home/ubuntu/codebase/data/archive"


def get_time():
    return strftime("%H:%M:%S", gmtime())


def get_summary(
    task_id,
    s3_path,
    text,
    questions=["Summarize this customer service conversation?"],
    ratio=[0.0, 0.2],
    temperature=1.0,
    word_to_digit=True,
    generate_reason=False,
):
    unique_dirname = (
        datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        + str(uuid.uuid4())[:5]
        + "_"
        + str(task_id)
    )
    op_dir_path = os.path.join(ARCHIEVE_DIR, unique_dirname)
    os.makedirs(op_dir_path, exist_ok=True)
    text_path = os.path.join(op_dir_path, "text.txt")
    text_aggr_by_channel_path = os.path.join(op_dir_path, "0_text_aggr_by_channel.txt")

    if word_to_digit:
        text_symb2w_path = os.path.join(op_dir_path, "1_text_symb2w.txt")
        text_w2d_path = os.path.join(op_dir_path, "2_text_w2d.txt")
        text_rm_punc_path = os.path.join(op_dir_path, "3_text_rm_punc.txt")

    text_final_ip_path = os.path.join(op_dir_path, "4_text_final_ip_path.txt")

    summarization_path = os.path.join(op_dir_path, "5_summary.txt")
    summary_processed_path = os.path.join(op_dir_path, "6_summary_processed.txt")

    if not text:
        s3_util.download_file(s3_path, text_path)
        print(f"{get_time()} - downloaded file {s3_path} to {text_path}")
        text = open(text_path).read()
    else:
        with open(text_path, "w") as f:
            f.write(text)

    text = aggregate_by_channel(text)
    with open(text_aggr_by_channel_path, "w") as f:
        f.write(text)

    text = " ".join([tt for tt in text.split("\n") if tt])

    if word_to_digit:
        text = get_symbol_to_word(text)
        with open(text_symb2w_path, "w") as f:
            f.write(text)
        try:
            text = w2d_obj.text_to_int_dialog(text)
            with open(text_w2d_path, "w") as f:
                f.write(text)
        except FileNotFoundError:
            traceback.print_exc()

        # remove "oh" if we have numeric values only
        # another round of remove duplicates after turn merge

        text = clean_transcript(
            [text],
            phrases_removal=False,
            words_removal=False,
            after_number=True,
        )[0]
        with open(text_final_ip_path, "w") as f:
            f.write(text)
    else:
        text = clean_transcript([text], phrases_removal=False, words_removal=False)[0]
        with open(text_final_ip_path, "w") as f:
            f.write(text)

    # catch empty calls
    if len(text.split(" ")) < 26:
        summary_text = summary_processed = reason = "Empty Call"
    else:
        ratios = [ratio for _ in range(len(questions))]
        summary_text, summary_processed, reason = test_summ_process.summarize(
            text_ip=text,
            questions=questions,
            ratios=ratios,
            temperature=temperature,
            generate_reason=generate_reason,
        )

    with open(summarization_path, "w") as f:
        f.write(summary_text)

    with open(summary_processed_path, "w") as f:
        f.write(summary_processed)

    print(f"{get_time()} - summarization completed for - {op_dir_path}")

    s3_path = (
        f"s3://{settings.S3_UPLOAD_BUCKET}/{settings.S3_FOLDER_PATH}/{unique_dirname}"
    )
    # s3_util.upload_folder(op_dir_path, s3_path)

    return summary_processed, reason, summarization_path


if __name__ == "__main__":
    import glob

    text_dir_path = "/home/ubuntu/codebase/data/mdt/transcripts/"
    op_path = "/home/ubuntu/codebase/data/testdata/test_results"
    text_files = glob.glob(f"{text_dir_path}/*.txt")

    unique_dirname = (
        datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + str(uuid.uuid4())[:5]
    )
    op_dir_path = os.path.join(op_path, unique_dirname)
    os.makedirs(op_dir_path, exist_ok=True)

    task_id = 12345
    s3_path = None
    general_summary = False
    word_to_digit = False
    question = "Summarize this conversation with details?"
    ratio = [0.05, 0.1]
    temperature = 1.0
    if general_summary:
        word_to_digit = True
        question = "Summarize this customer service conversation?"
        ratio = [0.0, 0.1]
        temperature = 0.5

    for text_file in text_files:
        text = open(text_file).read()
        if general_summary:
            text = text.replace("Caller:", "Customer:")
        start = time.perf_counter()
        summary_processed, reason, summarization_path = get_summary(
            task_id,
            s3_path,
            text,
            ratio=ratio,
            temperature=temperature,
            word_to_digit=word_to_digit,
            questions=[question],
        )
        end = time.perf_counter()
        print(f"{text_file}: {end-start}")
        summary_processed_path = os.path.join(op_dir_path, os.path.basename(text_file))
        with open(summary_processed_path, "w") as f:
            f.write(summary_processed)
