from __future__ import annotations

from collections.abc import Awaitable, Callable

import aio_pika

from packages.messaging.messages import JobMessage
from packages.messaging.topology import declare_topology, queue_names

JobHandler = Callable[[JobMessage], Awaitable[None]]


class RabbitWorker:
    """Consume durable jobs with bounded retries and explicit dead-lettering."""

    def __init__(
        self,
        connection: aio_pika.abc.AbstractRobustConnection,
        queue_name: str,
        handler: JobHandler,
    ) -> None:
        self.connection = connection
        self.queue_name = queue_name
        self.handler = handler

    async def consume(self) -> None:
        channel = await self.connection.channel()
        await declare_topology(channel)
        queue = await channel.get_queue(self.queue_name)
        async with queue.iterator() as iterator:
            async for message in iterator:
                await self._handle(channel, message)

    async def _handle(
        self,
        channel: aio_pika.abc.AbstractChannel,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        try:
            job = self._decode(message.body)
            await self.handler(job)
        except Exception:
            await self._retry_or_dead_letter(channel, message)
        else:
            await message.ack()

    async def _retry_or_dead_letter(
        self,
        channel: aio_pika.abc.AbstractChannel,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        job = self._decode(message.body)
        if job.attempt < job.max_attempts:
            retry = await channel.get_exchange("trading")
            retry_job = JobMessage(
                job_id=job.job_id,
                job_type=job.job_type,
                payload=job.payload,
                session_id=job.session_id,
                experiment_id=job.experiment_id,
                attempt=job.attempt + 1,
                max_attempts=job.max_attempts,
                created_at=job.created_at,
            )
            await retry.publish(
                aio_pika.Message(
                    retry_job.to_bytes(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    message_id=str(retry_job.job_id),
                    type=retry_job.job_type,
                ),
                routing_key=queue_names(self.queue_name).retry,
            )
            await message.ack()
            return
        await message.reject(requeue=False)

    @staticmethod
    def _decode(body: bytes) -> JobMessage:
        import json
        from datetime import datetime
        from uuid import UUID

        value = json.loads(body)
        return JobMessage(
            job_id=UUID(value["job_id"]),
            job_type=value["job_type"],
            payload=value["payload"],
            session_id=UUID(value["session_id"]) if value.get("session_id") else None,
            experiment_id=UUID(value["experiment_id"]) if value.get("experiment_id") else None,
            attempt=int(value.get("attempt", 1)),
            max_attempts=int(value.get("max_attempts", 3)),
            created_at=datetime.fromisoformat(value["created_at"]) if value.get("created_at") else None,
        )


async def run_worker(
    connection: aio_pika.abc.AbstractRobustConnection,
    queue_name: str,
    handler: JobHandler,
) -> None:
    worker = RabbitWorker(connection, queue_name, handler)
    await worker.consume()
