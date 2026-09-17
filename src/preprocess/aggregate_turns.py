import re


def format_dialogue_text(dialogue_text: str, dialogue_identifiers: list, remove_speaker: bool):

    dialogue_lines = dialogue_text.splitlines()
    formatted_dialogue_lines = []

    for dialogue_line in dialogue_lines:
        dialogue_line = dialogue_line.strip()

        if not len(dialogue_line):
            continue
        speaker = None
        for _speaker in dialogue_identifiers:
            if dialogue_line.startswith(f"{_speaker}:"):
                speaker = _speaker
                break
        if speaker is None:
            speaker_text = dialogue_line.split(f":", 1)
            if len(speaker_text) == 1:
                print(
                    f"WARNING: not able to aggregate turns for line {dialogue_line}")
                dialogue_text = dialogue_text.replace(
                    '\n', ' ').replace('\r', '')
                dialogue_text = re.sub(' {2,}', ' ', dialogue_text).strip()
                return dialogue_text

            elif len(speaker_text) == 2:
                speaker = speaker_text[0]

        dialogue_line_content = dialogue_line.split(f"{speaker}:", 1)[1]
        dialogue_line_content = dialogue_line_content.strip()

        if len(formatted_dialogue_lines) == 0:
            formatted_dialogue_lines.append([speaker, dialogue_line_content])
        elif formatted_dialogue_lines[-1][0] == speaker:
            formatted_dialogue_lines[-1][1] += f" {dialogue_line_content}"
        else:
            formatted_dialogue_lines.append([speaker, dialogue_line_content])

    dialogue_lines_op = []
    for speaker, utterence in formatted_dialogue_lines:
        if remove_speaker is False:
            dialogue_lines_op.append(f'{speaker}: {utterence}')
        else:
            dialogue_lines_op.append(utterence)

    if remove_speaker is False:
        dialogue_text_op = "\n".join(dialogue_lines_op)
    else:
        dialogue_text_op = " ".join(dialogue_lines_op)
        dialogue_text_op = " ".join(dialogue_text_op.split())

    return dialogue_text_op


if __name__ == "__main__":
    dialogue_text = """
    Caller: Hi
    Caller: Hello
    Agent: My name is ABC
    Agent: ABC
    Caller: My name is xyz and callback number is 1234567
    Agent: How can I help you today
    """

    dialogue_text = """
    Caller: Hi
    Caller: Hello
    Agent: My name is ABC

    Agent: ABC
    Caller: My name is xyz and callback number is 1234567
    Agent: How can I help you today
    Caller:
    """

    dialogue_text = """
    Caller1: Hi
    Caller: Hello
    agent: My name is ABC
    Agent: ABC
    Caller: My name is xyz and callback number is 1234567
    Agent: How can I help you today
    """

    dialogue_text = """
    Hi Hello My name
    is ABC ABC My name
    is xyz and callback
    number is 1234567 
    How can I help you today"""

    dialogue_text = """Hi Hello My name is ABC ABC My name is xyz and callback number is 1234567 How can I help you today"""

    print(format_dialogue_text(dialogue_text, dialogue_identifiers=[
          "Caller", "Agent"], remove_speaker=True))
