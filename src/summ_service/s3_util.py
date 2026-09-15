import logging
import re
import subprocess
from pathlib import Path
from typing import Union

import boto3
import botocore

s3_re = re.compile(r"s3://([^/]*)/(.*)")
s3 = boto3.client("s3")
logger = logging.getLogger(__name__)


def download_s3_fileobj(s3_path: str, fileobj):
    m = s3_re.match(s3_path)
    if not m:
        raise ValueError(f"{s3_path} is not a valid s3 path!")
    try:
        bucket = m[1]
        obj = m[2]
        s3.download_fileobj(bucket, obj, fileobj)
        fileobj.seek(0)
        return
    except botocore.exceptions.ClientError as error:
        logger.exception(f"boto3 error file download failed, {error}")
        return


def download_file(s3_path: str, download_path: Union[Path, str]):
    m = s3_re.match(s3_path)
    if not m:
        raise ValueError(f"{s3_path} is not a valid s3 path!")
    try:
        bucket = m[1]
        obj = m[2]
        s3.download_file(bucket, obj, str(download_path))
    except botocore.exceptions.ClientError as error:
        logger.error(f"boto3 error, use aws-cli instead. {error}")
        subprocess.check_call(["aws", "s3", "cp", s3_path, download_path])


# def upload_file(file_path, s3_upload_folder_path):
#     subprocess.call(["aws", "s3", "cp", file_path, s3_upload_folder_path])


# def upload_folder(folder_path, s3_upload_fotar cf - paths-to-archive |lder_path):
#     subprocess.call(
#         ["aws", "s3", "cp", folder_path, s3_upload_folder_path, "--recursive"]
#     )


if __name__ == "__main__":
    s3_path = "s3://rtg-nlp-pilot-code-pilot-us-east-1/demo-pilot-summarization/02-02-2021_13-16-05_sid_62492323_dbsid_540.wav"
    download_path = "/home/ubuntu/codebase/speech-to-text/data/"

    download_file(s3_path, download_path)
