"""Deterministic multiple-testing corrections with an explicit hypothesis universe."""

import math


def adjust(ps, method="BH", universe=None):
    if method not in ("BH", "BY") or any(not math.isfinite(p) or not 0 <= p <= 1 for p in ps):
        raise ValueError("Invalid correction or P values")
    n = len(ps) if universe is None else universe
    if n < len(ps):
        raise ValueError("Correction universe cannot omit tested hypotheses")
    factor = sum(1 / i for i in range(1, n + 1)) if method == "BY" else 1
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    result, previous = [1.0] * len(ps), 1.0
    for rank in range(len(ps), 0, -1):
        index = order[rank - 1]
        previous = min(previous, ps[index] * n * factor / rank)
        result[index] = previous
    return result
