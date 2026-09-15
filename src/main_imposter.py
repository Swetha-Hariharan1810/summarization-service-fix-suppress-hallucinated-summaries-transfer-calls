
import time
import random
import string


def get_summary(s3_path, text):

    time.sleep(random.randint(5, 10))
    transcript = ''.join(random.choices(
        string.ascii_uppercase + string.digits + " \n", k=random.randint(50, 500)))

    return transcript, None
