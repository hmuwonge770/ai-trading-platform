from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal


def simple_moving_average(values: Sequence[Decimal], window: int) -> list[Decimal | None]:
    """Return a rolling simple moving average without look-ahead or float conversion."""
    if window <= 0:
        raise ValueError("window must be greater than zero")

    result: list[Decimal | None] = [None] * len(values)
    rolling_sum = Decimal("0")

    for index, value in enumerate(values):
        rolling_sum += value
        if index >= window:
            rolling_sum -= values[index - window]
        if index >= window - 1:
            result[index] = rolling_sum / Decimal(window)

    return result
