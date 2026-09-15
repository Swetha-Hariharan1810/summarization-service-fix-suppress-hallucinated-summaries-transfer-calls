import logging.config
from pathlib import Path
import yaml


def setup_logging():
    with open(Path(__file__).parent / "logging-config.yaml", "r") as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)


setup_logging()

import datetime
import json
import os
import traceback

import torch
import time
import datetime
import tempfile

from rmq import constants, rmq_connection, schemas
import summ_main
from config import get_settings
from rmq import rmq_producer
from summ_service import s3_util
from summ_service.config import SummConfig
from summ_service.summ_model import SummModel


settings = get_settings()

logger = logging.getLogger(__name__)

# TODO: fetch config file from db server to support multiple models at production

summ_config = SummConfig()
models_dir = Path(__file__).parent.parent / "data" / "models"
summ_model = SummModel.from_pretrained(models_dir, summ_config)


def process_message(message_body: schemas.ReqBody):
    s3_path, text, reason_flag = (
        message_body.s3_path,
        message_body.text,
        message_body.reason_flag,
    )
    if message_body.summary_ratio:
        summ_model.config.ratio = message_body.summary_ratio
    if reason_flag:
        summ_model.config.generate_reason = True
    if not text:
        if not s3_path:
            logger.error("s3_path and text are both empty!")
            return {
                "summary": "",
            }
        with tempfile.TemporaryFile() as fp:
            s3_util.download_s3_fileobj(s3_path, fp)
            text = fp.read().decode("utf-8")
    summary_text, reason = summ_main.get_summary(text, summ_model)
    logger.debug(f"{summary_text=}")
    # TODO: generate response schema
    output_data = {
        "summary": summary_text,
    }
    if reason_flag:
        output_data["reason"] = reason

    return output_data


def start_main():
    basic_message_sender = rmq_connection.BasicMessageSender(
        settings.RMQ_BROKER_ID,
        settings.RMQ_USERNAME,
        settings.RMQ_PASSWORD,
        settings.RMQ_AWS_REGION,
    )

    basic_message_sender.channel.queue_declare(
        queue=settings.IP_QUEUE_NAME, durable=True
    )

    def callback(ch, method, properties, body):
        logger.info(f"Message received {body=}")
        try:
            message: schemas.MessageSchema = schemas.MessageSchema.parse_obj(
                json.loads(body)
            )
        except Exception as e:
            logger.exception(f"Wrong message format: {e}")
            # retry is handled on platform, therefore we just acknowlege this msg
            basic_message_sender.channel.basic_ack(
                delivery_tag=method.delivery_tag
            )
            return
        try:
            # notify processing to RMQ server
            res = schemas.ResponseSchema(
                job_status=constants.PROCESSING,
                task_id=message.task_id,
                job_id=message.job_id,
            )
            rmq_producer.send_status_and_data(res)
            start_time_utc = str(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            logger.info(
                f"Start processing task: {message.task_id}, {start_time_utc=}"
            )
            start_proc_time = time.perf_counter()
            # process message
            output_data = process_message(message.req_body)
            proc_time = time.perf_counter() - start_proc_time
            complete_time_utc = str(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            logger.info(
                f"Finish processing task: {message.task_id},"
                f" {complete_time_utc=}"
            )
            logger.info(
                f"Processing time of task: {message.task_id}, {proc_time=}"
            )
            res = schemas.ResponseSchema(
                job_status=constants.COMPLETED,
                task_id=message.task_id,
                job_id=message.job_id,
                output_data=output_data,
                processing_time_started=start_time_utc,
                processing_time_completed=complete_time_utc,
            )
            rmq_producer.send_status_and_data(res)
            logger.info(
                f"Responded to platform task: {message.task_id}, {output_data=}"
            )
        except Exception as e:
            # notify fail status to server
            logger.exception(f"Exception in processing message {e}")
            failure_log = traceback.format_exc()
            res = schemas.ResponseSchema(
                job_status=constants.FAILED,
                task_id=message.task_id,
                job_id=message.job_id,
                failure_info=failure_log,
            )
            rmq_producer.send_status_and_data(res)

        # Retry is handled on platform
        basic_message_sender.channel.basic_ack(delivery_tag=method.delivery_tag)

    basic_message_sender.channel.basic_qos(prefetch_count=1)
    basic_message_sender.channel.basic_consume(
        queue=settings.IP_QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=False,
    )
    logger.info("Waiting for message")
    basic_message_sender.channel.start_consuming()


if __name__ == "__main__":
    logger.info(f"Start service: {settings.MODULE_NAME}")
    torch.set_num_threads(settings.NUM_THREADS)
    logger.info(
        "Setting service to use parallelization with"
        f" {settings.NUM_THREADS} cores"
    )
    try:
        start_main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            import sys

            sys.exit(0)
        except SystemExit:
            os._exit(0)
