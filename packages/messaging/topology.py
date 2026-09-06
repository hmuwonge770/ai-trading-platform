from __future__ import annotations

from dataclasses import dataclass

import aio_pika
from aio_pika import ExchangeType

EXCHANGE = "trading"
JOB_QUEUES = (
    "research.generate", "experiment.backtest", "validation.run", "critic.review",
    "execution.submit", "execution.reconcile",
)
RETRY_DELAY_MS = 5_000


@dataclass(frozen=True)
class QueueNames:
    retry: str
    dead: str


def queue_names(queue: str) -> QueueNames:
    return QueueNames(f"{queue}.retry", f"{queue}.dead")


async def declare_topology(channel: aio_pika.abc.AbstractChannel) -> None:
    """Declare durable exchange, work queues, retry queues and dead-letter queues."""
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.DIRECT, durable=True)
    for queue_name in JOB_QUEUES:
        names = queue_names(queue_name)
        dead = await channel.declare_queue(names.dead, durable=True)
        retry = await channel.declare_queue(
            names.retry,
            durable=True,
            arguments={
                "x-message-ttl": RETRY_DELAY_MS,
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": queue_name,
            },
        )
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": names.dead,
            },
        )
        await exchange.bind(retry, routing_key=names.retry)
        await exchange.bind(dead, routing_key=names.dead)
        await exchange.bind(queue, routing_key=queue_name)
