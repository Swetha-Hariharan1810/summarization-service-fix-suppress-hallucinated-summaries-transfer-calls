import re

word_to_digit = None


class WordToDigit:

    def __init__(self):
        self.units = [
            'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
            'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
            'sixteen', 'seventeen', 'eighteen', 'nineteen',
        ]
        self.tens = ['', '', 'twenty', 'thirty', 'forty',
                     'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        self.scales = ['hundred', 'thousand', 'million', 'billion', 'trillion']

        self.ordinal_words = {'first': 1, 'second': 2, 'third': 3,
                              'fifth': 5, 'eighth': 8, 'ninth': 9, 'twelfth': 12}
        self.ordinal_endings = [('ieth', 'y'), ('th', '')]

        self.numwords = {}
        self.numwords['and'] = (1, 0)
        for idx, word in enumerate(self.units):
            self.numwords[word] = (1, idx)
        for idx, word in enumerate(self.tens):
            self.numwords[word] = (1, idx * 10)
        for idx, word in enumerate(self.scales):
            self.numwords[word] = (10 ** (idx * 3 or 2), 0)

    def is_number(self, x):
        if type(x) == str:
            x = x.replace(',', '')
        if x.strip() in ["infinity", "nan"]:
            return False
        try:
            float(x)
            int(x)
        except:
            return False
        return True

    def is_numword(self, x):
        if x in self.numwords:
            return True
        if self.is_number(x):
            return True
        return False

    def from_numword(self, x):
        if self.is_number(x):
            scale = 0
            increment = int(x.replace(',', ''))
            return scale, increment
        return self.numwords[x]

    def format_tollfree_number(self, textnum):
        if "one eight hundred" in textnum:
            _textnum = textnum.replace(
                "one eight hundred", "one eight zero zero")
            op = self.text_to_int(_textnum)

            if re.search(r'\b\d{10,11}\b', op):
                return _textnum
            else:
                return textnum
        else:
            return textnum

    def text_to_int_dialog(self, textnum: str):
        dialoge_lines = textnum.splitlines()
        op_dialoge_lines = []
        for dialoge_line in dialoge_lines:
            w2d_dialoge_line = self.text_to_int(dialoge_line)
            op_dialoge_lines.append(w2d_dialoge_line)
        return "\n".join(op_dialoge_lines)

    def text_to_int(self, textnum):
        escape_phrases = ["one second", "other one is",
                          "one more question", "first name is", "first and last name",
                          "my first available", "My first available", "choose one from",
                          "one moment", "o'clock"]
        textnum = escape(textnum, escape_phrases)

        textnum = textnum.replace('-', ' ')
        textnum = self.format_tollfree_number(textnum)

        current = result = p_increment = 0
        curstring = ''
        suffix = ''
        onnumber = False
        lastunit = False
        lastscale = False
        last_th_word = False

        last_word = False

        for word in textnum.split():

            if word.isdigit():
                curstring = curstring + " " + word + " "
                continue

            if word in self.ordinal_words:
                scale, increment = (1, self.ordinal_words[word])
                current = current * scale + increment
                if scale > 100:
                    result += current
                    current = 0
                suffix = word[-2:]

                curstring += repr(result + current) + suffix + " "
                result = current = 0
                onnumber = False
                lastunit = False
                lastscale = False
                last_th_word = False
                suffix = ''
            else:
                for ending, replacement in self.ordinal_endings:
                    if word.endswith(ending):
                        _w = "%s%s" % (word[:-len(ending)], replacement)
                        # _w, _ = word.split(ending)
                        if _w in self.numwords:
                            word = _w
                            last_th_word = True
                            break

                if (not self.is_numword(word)) or (word == 'and' and not lastscale):
                    if onnumber:
                        # Flush the current number we are building
                        if last_th_word:
                            curstring += repr(result + current) + "th "
                        elif suffix:
                            curstring += repr(result + current) + suffix + " "
                        else:
                            curstring += repr(result + current) + " "
                    curstring += word + " "
                    result = current = 0
                    onnumber = False
                    lastunit = False
                    lastscale = False
                    last_th_word = False
                    suffix = ''

                else:
                    scale, increment = self.from_numword(word)
                    onnumber = True

                    if lastunit and (word not in self.scales):
                        # Assume this is part of a string of individual numbers to
                        # be flushed, such as a zipcode "one two three four five"
                        curstring += repr(result + current)
                        result = current = 0

                    if scale > 1:
                        current = max(1, current)

                    # if last_word and last_word.isdigit() and word.isdigit():
                    #     # special case "twenty twenty"
                    #     # without this condition the output would be 20+20 -> 40
                    #     # curstring = curstring + " " + word
                    #     # continue
                    #     current = int(str(last_word) + str(word))

                    # if word.isdigit():
                    #     # special case "twenty twenty"
                    #     # without this condition the output would be 20+20 -> 40
                    #     curstring = curstring + " " + word
                    #     continue
                    #     # current = int(str(last_word) + str(word))

                    if len(str(increment)) >= 2 and len(str(increment)) >= len(str(p_increment)) and p_increment != 0:
                        # special case "twenty twenty"
                        # without this condition the output would be 20+20 -> 40
                        current = int(str(current) + str(increment))
                    else:
                        current = current * scale + increment
                    if scale > 100:
                        result += current
                        current = 0

                    lastscale = False
                    lastunit = False
                    if word in self.scales:
                        lastscale = True
                    elif word in self.units:
                        lastunit = True

                    p_increment = increment

            last_word = word

        if onnumber:
            if last_th_word:
                curstring += repr(result + current) + "th "
            elif suffix:
                curstring += repr(result + current) + suffix + " "
            else:
                curstring += repr(result + current) + " "

        # handle corner cases for "one of the" string
        curstring = re.sub(r"\b1\sof\b", "one of", curstring)

        # handle corner cases for "on one side of" string
        curstring = re.sub(r"\bon\s1\sside\sof\b", "on one side of", curstring)

        # handle special case where O or Oh is present in between the digits which signifies 0
        curstring = re.sub(r"(\d+)\soh?\s(\d+)", r"\g<1>0\g<2>", curstring)
        curstring = re.sub(r"\boh?\s(\d+)\b", r"0\g<1>", curstring)
        curstring = re.sub(r"\b(\d+)\soh?\b", r"\g<1>0", curstring)

        # point replacement 4 point 8 ==> 4.8
        curstring = re.sub(r"(\d+)\spoint\s(\d+)", r"\g<1>.\g<2>", curstring)

        # the reading was point 2 ==> the reading was 0.2
        curstring = re.sub(
            r"\b([a-zA-Z]+)\spoint\s(\d+)\b", r"\g<1> 0.\g<2>", curstring)

        # removal of one and ten why? removed for now
        # curstring = re.sub(r"(\D+)\s10?\s(\D+)",
        #                    r"\g<1> \g<2>", curstring.strip())
        curstring = re.sub(r"\A10?\s(\D+)", r"\g<1>", curstring.strip())
        curstring = re.sub(r"(\D+)\s10?\Z", r"\g<1>", curstring.strip())

        # handling escaped characters
        curstring = re.sub(r"\={2}", " ", curstring)
        curstring = re.sub(r" {2}", " ", curstring)

        return curstring.strip()


def escape(text, phrases):
    for p in phrases:
        if p in text:
            text = re.sub(rf"\b{re.escape(p)}\b",
                          "==" + p.replace(" ", "==") + "==", text, re.I)
    return text


# def convert_word_to_num(text):
#     word_to_digit = WordToDigit()

#     escape_phrases = ["one second"]

#     text = escape(text, escape_phrases)
#     op = word_to_digit.text_to_int(text)

#     return op


def get_word_to_digit():
    global word_to_digit
    if word_to_digit is None:
        word_to_digit = WordToDigit()

    return word_to_digit


if __name__ == "__main__":

    text = "Monday to Saturday from 8:00 o'clock in the morning"
    # text = "Monday to Saturday from 8 00 o'clock in the morning"
    text = "Monday to Saturday from 800 in the morning"
    text = "Monday to Saturday from 801 111 o'clock in the morning"
    # text = "Monday to Saturday from 80 10 o'clock in the morning"
    # text = "Monday to Saturday from 80 10 00 o'clock in the morning"

    word_to_digit = WordToDigit()
    text_num = word_to_digit.text_to_int(text)

    print(f"{text_num=}")