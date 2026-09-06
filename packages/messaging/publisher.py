from __future__ import annotations

import aio_pika
from aio_pika import DeliveryMode, Message

from packages.messaging.messages import JobMessage
from packages.messaging.topology import EXCHANGE


class RabbitPublisher:
    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection):
        self.connection = connection

    async def publish(self, message: JobMessage) -> None:
        channel = await self.connection.channel(publisher_confirms=True)
        try:
            exchange = await channel.get_exchange(EXCHANGE)
            await exchange.publish(
                Message(
                    message.to_bytes(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    message_id=str(message.job_id),
                    type=message.job_type,
                    headers={"attempt": message.attempt, "max_attempts": message.max_attempts},
                ),
                routing_key=message.job_type,
            )
        finally:
            await channel.close()
