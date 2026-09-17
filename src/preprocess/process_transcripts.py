import re

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
    text = text.split('.')
    cnt = len(text)
    for i, cc in enumerate(text):
        cc = cc.strip()
        if cc and cc[-1].isdigit() and i+1 < cnt and text[i+1].strip() and text[i+1].strip()[0].isdigit():
            cc += '.'
        if cc:
            new_c.append(cc)
    new_c = ' '.join(new_c)
    new_c = ' '.join([cc for cc in new_c.split(' ') if cc])
    return new_c

def remove_punc(text):
    punc = '''!()-[]{};:"\,<>/?#^&*_~-–'''
    text = text.encode('ascii', 'ignore').decode('ascii').strip().replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
    for p in punc:
        text = text.replace(p, ' ')
    text = remove_period(text)
    return text

def aggregate_by_channel(text):
    single_word_exception = set(['thank', 'great', 'awesome', 'gotcha', 'understood', 'understandable', 'terrific', 'wonderful', 'excellent'])
    pre_turn_id = ''
    processed_turns = []
    turns = text.split('\n')
    for turn in turns:
        turn = turn.encode('ascii', 'ignore').decode('ascii').replace('`', "'").replace("’", "'").strip()
        if not turn: continue
        turn = turn.lower().strip()
        if ':' not in turn:
            turn_id = pre_turn_id
            context = turn
        else:
            turn_id, context = turn.split(':', 1)
            turn_id = turn_id.strip()
            context = context.strip()
        if 'unknown' in turn_id or 'mono' in turn_id:
            turn_id = ''
        context = remove_punc(context)
        context = clean_transcript([context])[0]
        if not context: continue
        if len(context.split(' ')) == 1 and context != 'yes'\
            and (len(context) < 5 or context in single_word_exception): continue
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
            joined_processed_turns.append(turn_id + ': ' + context)

    # mdt clean up
    if joined_processed_turns and joined_processed_turns[0].startswith('Caller:'):
        joined_processed_turns = joined_processed_turns[1:]
    return "\n".join(joined_processed_turns)

def remove_duplicates(trans, remove_repeats):
    numbers = set(['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred', 'thousand', 'oh'])
    trans = trans.split(' ')
    keep = [1 for _ in range(len(trans))]
    for idx in range(1, len(trans)):
        for j in range(1, remove_repeats+1):
            j = min(min(j, idx), len(trans) - idx)
            if trans[idx - j: idx] == trans[idx: idx + j]:
                keep[idx - j: idx] = [0 for _ in range(j)]

    # keep duplicate numbers
    for idx, (k, t) in enumerate(zip(keep, trans)):
        if not k and t in numbers:
            keep[idx] = True

    return " ".join([t for idx, t in enumerate(trans) if keep[idx]])

def truncate_by_phrase(transcripts, phrases, threshold=15):
    for phrase in phrases:
        idxs = [t.find(phrase) for t in transcripts]
        transcripts = [t[idx+len(phrase):].strip() if idx != -1 and idx < threshold else t.strip() for t, idx in zip(transcripts, idxs)]
    return transcripts

def clean_transcript(transcripts, sentences_removal=True, phrases_removal=True, words_removal=True, remove_repeats=3, cutten_phrases=[], cutten_idx=15, after_number=False):

    remove_sentences = ['call may be monitored or recorded for quality and training purposes',
                        'call may be monitored or recorded for the quality purposes',
                        'we are experiencing high call volumes therefore you may experience longer hold times',
                        'all consultants are currently assisting other callers remain on the line and your call will be answered in the order it was received',
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
                        "i have a lot of trouble hearing you"
                        "i have trouble hearing you",
                        "i can help you with that",
                        "i can certainly help you with that",
                        'thank you so much for the help',
                        'thank you so much for your help', 
                        'thank you very much for calling',
                        'thank you so much for calling',
                        'thank you very much for your help',
                        'thank you very much for the help',
                        'have a good rest of your day',
                        "sorry to hear about the problem",
    ]

    remove_phrases = [
                      "i can help you with",
                      "i'm doing pretty well",
                      "i'm doing pretty good",
                      "how can i help you",
                      'hold on a second',
                      'good morning',
                      'good afternoon',
                      'good evening',
                      'how are you',
                      'how are you doing',
                      'hold on', 
                      'good luck', 
                      'hi there',
                      'and so',
                      "give me one second here",
                      "give me one second",
                      "give me a moment",
                      'give me one moment',
                      'a moment',
                      "one moment",
                      "one second",
                      'i appreciate',
                      'i appreciated',
                      'i appreciate it',
                      "you're welcome", 
                      'sorry to hear that', 
                      'thank you very much',
                      'thank you so much',
                      'thanks so much',
                      'thanks very much',
                      'have a good day',
                      'have a good night',
                      'have a good evening',
                      "have a nice day",
                      'my goodness',
                      'my god',
                      'my godness',
                      'thank you for calling',
                      'thanks for calling',
                      'thank you',
                      'excuse me',
                      'no problem',
                      'there we go',
                      'like i said',
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
                      'you too',
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
                      "sorry to hear that",
                      "and then",
                      "mm hmm",
                      "uh huh"
    ]

    remove_words = ['sorry', 'gosh', 'lol', 'definitely', 'cheers', 
                    'wow', 'fantastic', 'goodbye', 'bye', 'yep',
                    'lovely', 'please', "ma'am", 'sir', 'well', 'really',
                    'hee', 'al', 'huh', 'uhm', 'oooo', 'ooo', 'oo', 'uh', 'mhmm', 'hmm',
                    'aa', 'o o', 'aaa', 'ha', 'a a', 'aha', 'um',
                    'hello', 'hi', 'hey', 'welcome', 'haha', 'aaa', 'al', 'amen',
                    'mam', 'ah', 'aye ', 'ap', 'tha', 'ana',
                    'yeah', 'yay', 'yap', 'thanks', 'okay', 'ok', 'sure',
                    'exactly', 'absolutely', 'certainly', "actually", 'brilliant', 'perfect'
    ]

    transcripts= [t.replace(' 1 ', ' one ').replace('1st ', 'first ').replace(' 2nd ', ' second ') for t in transcripts]
    if sentences_removal:
        remove_sentences = sorted(remove_sentences, key=lambda x: -len(x))
        for sent in remove_sentences:
            transcripts = [t.replace(sent, '') for t in transcripts]
    if phrases_removal:
        remove_phrases = sorted(remove_phrases, key=lambda x: -len(x))
        for phrase in remove_phrases:
            phrase = ' ' + phrase
            transcripts = [(' ' + t + ' ').replace(phrase, '').strip() for t in transcripts]
    if words_removal:
        if after_number:
            remove_words += ['oh']
        remove_words = sorted(remove_words, key=lambda x: -len(x))
        for word in remove_words:
            word = ' ' + word + ' '
            transcripts = [(' ' + t + ' ').replace(word, ' ').strip() for t in transcripts]
    if remove_repeats > 0:
        transcripts= [remove_duplicates(t, remove_repeats) for t in transcripts]
    if len(cutten_phrases) > 0:
        transcripts = truncate_by_phrase(transcripts, cutten_phrases, cutten_idx)
    return [" ".join([t for t in transcript.split(' ') if t]) for transcript in transcripts]

_CALLER_LABELS = ("caller", "customer", "patient", "cust", "cx")
_AGENT_LABELS = ("agent", "rep", "csr", "operator", "advisor", "associate")

# Bracketed redaction placeholders
_REDACTION_RE = re.compile(r"\[[^\]]*\]")

# Spoken numbers. 
_NUMBER_WORDS = set("""
zero one two three four five six seven eight nine ten eleven twelve thirteen
fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty
sixty seventy eighty ninety hundred thousand oh number numbers
january february march april may june july august september october november december
""".split())


def has_caller_channel(text):
    """
    True if the transcript has at least one turn labelled as the caller.
    """
    for line in (text or "").split("\n"):
        if ":" not in line:
            continue
        label = line.split(":", 1)[0].strip().lower()
        if "unknown" in label or "mono" in label:
            continue
        if any(k in label for k in _CALLER_LABELS):
            return True
    return False


def get_caller_turns(text):
    """Concatenate the caller-side turns of a raw transcript.

    Reads the RAW transcript rather than the output of aggregate_by_channel,
    because that function drops the opening turn when it belongs to the caller
    and discards most single-word turns -- on short calls that is exactly the
    content we need to measure.
    """
    parts, current = [], None
    for line in (text or "").split("\n"):
        line = (
            line.encode("ascii", "ignore")
            .decode("ascii")
            .replace("`", "'")
            .replace("\u2019", "'")
            .strip()
        )
        if not line:
            continue
        body = line
        if ":" in line:
            label, body = line.split(":", 1)
            label = label.strip().lower()
            if "unknown" in label or "mono" in label:
                pass  # unlabelled channel: keep the previous speaker
            elif any(k in label for k in _CALLER_LABELS):
                current = "caller"
            elif any(k in label for k in _AGENT_LABELS):
                current = "agent"
        body = body.strip().lower()
        if body and current == "caller":
            parts.append(body)
    return " ".join(parts)


def clean_transfer(text, drop_numbers=True):
    """Caller-side content words only, with pleasantries and numbers removed.

    Used to decide whether a routing/transfer call contains enough caller
    speech to summarise. On a call handed off before the caller stated a
    reason, the caller says only a name, a callback number and an
    acknowledgement, all of which this strips, leaving 0-4 residual tokens.

    Names cannot be removed by a word list and survive as 2-3 tokens; that is
    small enough not to affect a length comparison against a ~40 word summary.

    Returns a whitespace-joined string (not a list, unlike clean_transcript).
    """
    caller = get_caller_turns(text)
    caller = _REDACTION_RE.sub(" ", caller)
    caller = remove_punc(caller)
    caller = clean_transcript(
        [caller],
        sentences_removal=True,
        phrases_removal=True,
        words_removal=True,
        after_number=True,
    )[0]
    tokens = [t for t in caller.split() if t]
    if drop_numbers:
        tokens = [
            t
            for t in tokens
            if t not in _NUMBER_WORDS and not any(c.isdigit() for c in t)
        ]
    return " ".join(tokens)