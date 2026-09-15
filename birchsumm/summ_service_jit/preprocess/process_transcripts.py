def get_symbol_to_word(text):
    replace_list = [
        ["%", " percent "],
        ["<", " smaller "],
        [">", " larger "],
        ["=", " equal "],
        ["#", " number "],
        ["&", " and "],
        ["+", " plus "],
        ["£", " pounds "],
        ["¥", " yen "],
        ["$", " dollar "],
        ["€", " euro "],
        ["/", " or "],
        ["@", " at "],
        ["-", " "],
        ["’", "'"],
    ]

    for replace_this, with_that in replace_list:
        text = text.replace(replace_this, with_that)
    return text


def remove_period(text):
    new_c = []
    text = text.split(".")
    cnt = len(text)
    for i, cc in enumerate(text):
        cc = cc.strip()
        if (
            cc
            and cc[-1].isdigit()
            and i + 1 < cnt
            and text[i + 1].strip()
            and text[i + 1].strip()[0].isdigit()
        ):
            cc += "."
        if cc:
            new_c.append(cc)
    new_c = " ".join(new_c)
    new_c = " ".join([cc for cc in new_c.split(" ") if cc])
    return new_c


def remove_punc(text):
    punc = """!()-[]{};:",<>/?#^&*_~-–"""
    text = (
        text.encode("ascii", "ignore")
        .decode("ascii")
        .strip()
        .replace("\n", " ")
        .replace("\t", " ")
        .replace("\r", " ")
    )
    for p in punc:
        text = text.replace(p, " ")
    text = remove_period(text)
    return text


def aggregate_by_channel(text, remove_speakerid=False):
    pre_turn_id = ""
    processed_turns = []
    turns = text.split("\n")
    for turn in turns:
        turn = (
            turn.encode("ascii", "ignore")
            .decode("ascii")
            .replace("`", "'")
            .replace("’", "'")
            .strip()
        )
        if not turn:
            continue
        turn = turn.lower().strip()
        if ":" not in turn:
            turn_id = pre_turn_id
            context = turn
        else:
            turn_id, context = turn.split(":", 1)
            turn_id = turn_id.strip()
            context = context.strip()
        if "unknown" in turn_id or "mono" in turn_id:
            turn_id = ""
        context = remove_punc(context)
        context = clean_transcript([context])[0]
        if not context or len(context.split(" ")) == 1:
            continue
        if turn_id == pre_turn_id and processed_turns:
            processed_turns[-1][1] += " " + context
        else:
            processed_turns.append([turn_id, context])
        pre_turn_id = turn_id
    joined_processed_turns = []
    for turn_id, context in processed_turns:
        if len(turn_id) == 0:
            joined_processed_turns.append(context)
        else:
            turn_id = turn_id[0].upper() + turn_id[1:].lower()
            joined_processed_turns.append(turn_id + ": " + context)
    return "\n".join(joined_processed_turns)


def remove_duplicates(trans, remove_repeats):
    trans = trans.split(" ")
    keep = [1 for _ in range(len(trans))]
    for idx in range(1, len(trans)):
        for j in range(1, remove_repeats + 1):
            j = min(min(j, idx), len(trans) - idx)
            if trans[idx - j : idx] == trans[idx : idx + j]:
                keep[idx - j : idx] = [0 for _ in range(j)]
    return " ".join([t for idx, t in enumerate(trans) if keep[idx]])


def truncate_by_phrase(transcripts, phrases, threshold=15):
    for phrase in phrases:
        idxs = [t.find(phrase) for t in transcripts]
        transcripts = [
            t[idx + len(phrase) :].strip()
            if idx != -1 and idx < threshold
            else t.strip()
            for t, idx in zip(transcripts, idxs)
        ]
    return transcripts


def clean_transcript(
    transcripts,
    sentences_removal=False,
    phrases_removal=True,
    words_removal=True,
    remove_repeats=3,
    cutten_phrases=[],
    cutten_idx=15,
    after_number=False,
):
    remove_sentences = []

    remove_phrases = [
        "i'm having a little bit of trouble hearing you",
        "i'm having a little trouble hearing you",
        "i'm having trouble hearing you",
        "i'm still having trouble hearing you",
        "i'm still having a little trouble hearing you",
        "i'm kind of having trouble hearing you",
        "i was having a little trouble hearing you",
        "i'm just having a lot of trouble hearing you",
        "i'm having a lot of trouble hearing you",
        "i've been having trouble hearing you",
        "i've had the trouble hearing you",
        "i had trouble hearing you",
        "i have a lot of trouble hearing youi have trouble hearing you",
        "I can help you with that",
        "I can certainly help you with that",
        "I can help you with",
        "how can i help you",
        "hold on a second",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how are you doingi'm doing pretty well",
        "i'm doing pretty good",
        "hold on",
        "good luck",
        "hi there",
        "and so",
        "give me one second here",
        "give me one second",
        "give me a moment",
        "give me one moment",
        "a moment",
        "one moment",
        "one second",
        "i appreciate",
        "i appreciated",
        "i appreciate it",
        "you're welcome",
        "sorry to hear that",
        "thank you so much for the help",
        "thank you so much for your help",
        "thank you very much for calling",
        "thank you so much for calling",
        "thank you very much for your help",
        "thank you very much for the help",
        "thank you very much",
        "thank you so much",
        "thanks so much",
        "thanks very much",
        "have a good rest of your day",
        "have a good day",
        "have a good night",
        "have a good evening",
        "have a nice day",
        "my goodness",
        "my god",
        "my godness",
        "thank you for calling",
        "thanks for calling",
        "thank you",
        "excuse me",
        "no problem",
        "there we go",
        "like i said",
        "i'm so sorry",
        "i'm sorry",
        "sorry about this",
        "sorry about that",
        "i see",
        "for sure",
        "it's my pleasure",
        "to youtube",
        "come on",
        "yes sir",
        "pretty much",
        "you know",
        "here we go",
        "hang on for a seond",
        "hang on",
        "you too",
        "no worries",
        "go ahead",
        "very much",
        "of course",
        "my pleasure",
        "my pleasures",
        "that's lovely",
        "so lovely",
        "bye bye",
        "yeah yeah",
        "ok ok",
        "sorry to hear about the problem",
        "sorry to hear that",
        "and then",
    ]

    remove_words = [
        "sorry",
        "gosh",
        "lol",
        "definitely",
        "cheers",
        "wow",
        "fantastic",
        "goodbye",
        "bye",
        "yep",
        "lovely",
        "please",
        "ma'am",
        "sir",
        "well",
        "really",
        "hee",
        "al",
        "huh",
        "uhm",
        "oooo",
        "ooo",
        "oo",
        "uh",
        "aa",
        "o o",
        "aaa",
        "ha",
        "a a",
        "aha",
        "um",
        "hello",
        "hi",
        "hey",
        "welcome",
        "haha",
        "aaa",
        "al",
        "amen",
        "mam",
        "ah",
        "aye ",
        "ap",
        "tha",
        "ana",
        "yeah",
        "yay",
        "yap",
        "thanks",
        "okay",
        "ok",
        "sure",
        "exactly",
        "absolutely",
        "certainly",
        "actually",
        "brilliant",
        "perfect",
    ]

    transcripts = [
        t.replace(" 1 ", " one ").replace("1st ", "first ").replace(" 2nd ", " second ")
        for t in transcripts
    ]
    if sentences_removal:
        remove_sentences = sorted(remove_sentences, key=lambda x: -len(x))
        for sent in remove_sentences:
            transcripts = [t.replace(sent, "") for t in transcripts]
    if phrases_removal:
        remove_phrases = sorted(remove_phrases, key=lambda x: -len(x))
        for phrase in remove_phrases:
            phrase = " " + phrase
            transcripts = [
                (" " + t + " ").replace(phrase, "").strip() for t in transcripts
            ]
    if words_removal:
        if after_number:
            remove_words += ["oh"]
        remove_words = sorted(remove_words, key=lambda x: -len(x))
        for word in remove_words:
            word = " " + word + " "
            transcripts = [
                (" " + t + " ").replace(word, " ").strip() for t in transcripts
            ]
    if remove_repeats > 0:
        transcripts = [remove_duplicates(t, remove_repeats) for t in transcripts]
    if len(cutten_phrases) > 0:
        transcripts = truncate_by_phrase(transcripts, cutten_phrases, cutten_idx)
    return [
        " ".join([t for t in transcript.split(" ") if t]) for transcript in transcripts
    ]
