# Quote characters the decoder sometimes wraps a whole summary in.
_QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "\u201c": "\u201d",  # “ ”
    "\u2018": "\u2019",  # ‘ ’
    "\u00ab": "\u00bb",  # « »
}
_CLOSERS = set(_QUOTE_PAIRS.values())


def strip_wrapping_quotes(text):
    """Remove quote marks that enclose the entire summary.

    Only a matched opening/closing pair at the very ends is removed, so
    quoted speech inside the summary is left untouched. 
    """
    text = (text or "").strip()
    changed = True
    while changed and len(text) > 1:
        changed = False
        body, trailing = text, ""
        if body.endswith(".") and len(body) > 1 and body[-2] in _CLOSERS:
            body, trailing = body[:-1], "."
        closer = _QUOTE_PAIRS.get(body[0])
        if closer and len(body) > 1 and body.endswith(closer):
            text = (body[1:-1].strip() + trailing).strip()
            changed = True
    # Unbalanced opener from a truncated generation: drop it only when this
    # opener's matching closer appears nowhere else in the summary.
    if len(text) > 1 and text[0] in _QUOTE_PAIRS and _QUOTE_PAIRS[text[0]] not in text[1:]:
        text = text[1:].strip()
    return text


def mdt_post_process(text):
    text = strip_wrapping_quotes(text)
    text = text.replace(" RTM", " recharger")
    first_text = [x for x in text.split('.')[:3] if x]
    last_text = [x for x in text.split('.')[3:] if x]
    first_text = list(map(lambda x: x.replace(' for the treatment of bowel issues', ''), first_text))
    first_text = list(map(lambda x: x.replace(' for the treatment of bladder issues', ''), first_text))
    return '.'.join(first_text + last_text).strip() + '.'