import sys

import pika
import logging
from config import get_settings
from .schemas import ResponseSchema
from .rmq_connection import BasicMessageSender

log = logging.getLogger(__name__)

# TODO: move to config
settings = get_settings()


def send_status_and_data(response: ResponseSchema):
    # TODO: move connection to singleton - no need to create connection every request
    # and no need to close the connection after the request ends

    basic_message_sender = BasicMessageSender(
        settings.RMQ_BROKER_ID,
        settings.RMQ_USERNAME,
        settings.RMQ_PASSWORD,
        settings.RMQ_AWS_REGION,
    )

    # TODO: move queue names to settings
    basic_message_sender.channel.queue_declare(
        queue=settings.RESP_QUEUE_NAME, durable=True
    )

    basic_message_sender.channel.basic_publish(
        exchange="",
        routing_key=settings.RESP_QUEUE_NAME,
        body=response.json(),
        properties=pika.BasicProperties(
            delivery_mode=2,
        ),
    )
    basic_message_sender.close()
    return True
