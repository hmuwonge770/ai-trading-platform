from __future__ import annotations

import aio_pika

from packages.messaging.topology import declare_topology
from packages.trading.config import get_settings


async def connect_rabbitmq() -> aio_pika.abc.AbstractRobustConnection:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await declare_topology(channel)
    await channel.close()
    return connection
