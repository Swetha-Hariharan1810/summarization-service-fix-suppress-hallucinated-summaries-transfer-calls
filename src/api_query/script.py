
import time
import requests

__author__ = "Gaurav Shegokar, BirchAI"

URL = "PROVIDED_BIRCHAI_PLATFORM_ENDPOINT_URL"
API_KEY = "PROVIDED_BIRCHAI_PLATFORM_API_KEY"

# task statuses
QUEUED = "QUEUED"
PROCESSING = "PROCESSING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
FAILED_RETRY = "FAILED_RETRY"

POLL_DURATION = 1


def get_header() -> dict:
    auth_header = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    return auth_header


def call_summ_api(text: str) -> tuple[bool, int, dict]:
    """Post call for the summarization api

    Args:
        text (str): text content of the transcript

    Returns:
        tuple[bool, int, dict]: api call success, task id, response dict
    """

    payload = {
        "text": text
    }

    response = requests.request(
        "POST", f"{URL}/api/summarization", headers=get_header(), json=payload)

    success_flag = True if response.status_code == 201 else False
    response_json = response.json()

    if success_flag is False:
        return success_flag, None

    task_id = response_json["task_id"]

    return success_flag, task_id, response_json


def get_all_tasks_for_user():
    params = {
        'limit': '100'
    }

    response = requests.request(
        "GET", f"{URL}/api/tasks", headers=get_header(), params=params)

    success_flag = True if response.status_code == 200 else False
    response_json = response.json()

    if success_flag is False:
        return success_flag, response_json

    return success_flag, response_json


def get_task_status(task_id: int) -> tuple[bool, bool, dict]:
    """ gets the status of the task request

    Args:
        task_id (int): task id of the request

    Returns:
        tuple[bool, bool, dict]: api call success, request completed, response dict
    """
    is_request_completed = False

    response = requests.request(
        "GET", f"{URL}/api/tasks/{task_id}", headers=get_header())

    success_flag = True if response.status_code == 200 else False
    response_json = response.json()

    if success_flag is False:
        return success_flag, is_request_completed, response_json

    if response_json["task_status"] in [QUEUED, PROCESSING]:
        is_request_completed = False
    elif response_json["task_status"] in [COMPLETED, FAILED, FAILED_RETRY]:
        is_request_completed = True
    else:
        success_flag = False

    return success_flag, is_request_completed, response_json


def get_task_results(task_id: int) -> tuple[bool, str, dict]:
    """gets the result of the task, that is summary for the transcript

    Args:
        task_id (int): task id of the summary request

    Returns:
        tuple[bool, str, dict]: api call success, summary, response dict
    """
    response = requests.request(
        "GET", f"{URL}/api/tasks/{task_id}/result", headers=get_header())

    summary = None

    success_flag = True if response.status_code == 200 else False
    response_json = response.json()

    if success_flag is False:
        return success_flag, summary, response_json

    summary = response_json["output_data"]["summary"]

    return success_flag, summary, response_json


def get_summary_for_transcript_file(transcript_file_path: str) -> tuple[bool, str]:
    """gets the summary for the transcript file path

    Args:
        transcript_file_path (str): transcript file path 

    Returns:
        tuple[bool, str]: summary request successful, summary for the transcript file
    """
    print(f"Getting Summary for file {transcript_file_path}")
    summary = ""
    text = open(transcript_file_path).read().strip()

    success_flag, task_id, response_json = call_summ_api(text)

    if success_flag is False:
        print(f"exception occured in call_summ_api -> {response_json}")
        return success_flag, summary

    # polling on API every X seconds till we get result
    print(f"Task ID for file {transcript_file_path} -> {task_id}")
    while True:
        print(f"polling on task {task_id} every {POLL_DURATION}s")
        success_flag, is_request_completed, response_json = get_task_status(
            task_id)
        if success_flag is False:
            break
        if is_request_completed is False:
            time.sleep(POLL_DURATION)
            continue

        if is_request_completed is True:
            print(
                f"summary available for task {task_id}")
            break

    if success_flag is False:
        print(
            f"exception occured in get_task_status for task id {task_id} -> {response_json}")
        return success_flag, summary

    success_flag, summary, response_json = get_task_results(task_id)
    if success_flag is False:
        print(
            f"exception occured in get_task_results for task id {task_id} -> {response_json}")
        return success_flag, summary

    return success_flag, summary


if __name__ == "__main__":

    transcript_file_paths = [
        "PATH_TO_TRANSCRIPT_FILE_1", "PATH_TO_TRANSCRIPT_FILE_2", ..., "PATH_TO_TRANSCRIPT_FILE_N"]
    for transcript_file_path in transcript_file_paths:
        success_flag, summary = get_summary_for_transcript_file(
            transcript_file_path)

        if success_flag is False:
            print(
                f"summary extraction failed for file {transcript_file_path}")
        else:
            print(f"summary for file {transcript_file_path} -> \n{summary}\n")
