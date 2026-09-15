import script
import pandas as pd

if __name__ == "__main__":
    """
    script to export all the api calls for summary
    """

    summaries = []
    ip_texts = []
    task_ids = []
    completion_dates = []
    request_status, tasks = script.get_all_tasks_for_user()

    for task in tasks:
        _, summary, response_json = script.get_task_results(task["id"])

        ip_text = response_json["request_params"]["text"]
        summaries.append(summary)
        ip_texts.append(ip_text)
        task_ids.append(task["id"])
        completion_dates.append(task["task_creation_date"])

    df = pd.DataFrame(
        {"Task_id": task_ids, "date": completion_dates,
         "input_text": ip_texts, "summary": summaries})

    df.sort_values('Task_id', inplace=True)
    df.to_csv('op_verint_test_dec.csv',
                index=False)
