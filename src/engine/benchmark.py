"""Benchmark abstraction.

No benchmark is hard-coded. A benchmark is anything that can produce a return
series over a date range, so a market index, a cash rate or a custom blend all
plug in the same way. Phase 2 establishes the interface; external price data
arrives later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence


@dataclass(frozen=True)
class BenchmarkDefinition:
    identifier: str
    name: str
    currency: str
    price_source: str          # where the series comes from, for provenance
    # "price_return" (index level only) or "total_return" (dividends
    # reinvested). Comparing a portfolio's total return against a benchmark's
    # price return silently understates outperformance -- see
    # docs/analytics.md "Benchmark caveats". Required, not inferred, because
    # getting it wrong is worse than being asked.
    return_methodology: str = "price_return"
    rebalancing_methodology: str | None = None   # e.g. "quarterly", None if N/A


class Benchmark(Protocol):
    @property
    def definition(self) -> BenchmarkDefinition: ...

    def return_series(self, dates: Sequence[date]) -> list[Decimal | None]:
        """Period returns between consecutive dates. None where unavailable."""
        ...


class StaticBenchmark:
    """A benchmark backed by a known level series. Useful for tests, and the
    shape any real price feed will be adapted into."""

    def __init__(self, definition: BenchmarkDefinition,
                 levels: dict[date, Decimal]):
        self._definition = definition
        self._levels = dict(levels)

    @property
    def definition(self) -> BenchmarkDefinition:
        return self._definition

    def level(self, on: date) -> Decimal | None:
        return self._levels.get(on)

    def return_series(self, dates: Sequence[date]) -> list[Decimal | None]:
        out: list[Decimal | None] = []
        for previous, current in zip(dates, dates[1:]):
            before, after = self._levels.get(previous), self._levels.get(current)
            if before is None or after is None or before == 0:
                out.append(None)
            else:
                out.append(after / before - 1)
        return out


class BenchmarkRegistry:
    """Named benchmarks, so callers ask for one by identifier rather than
    constructing it and embedding a choice in the calculation code."""

    def __init__(self) -> None:
        self._benchmarks: dict[str, Benchmark] = {}

    def register(self, benchmark: Benchmark) -> None:
        self._benchmarks[benchmark.definition.identifier] = benchmark

    def get(self, identifier: str) -> Benchmark | None:
        return self._benchmarks.get(identifier)

    def all(self) -> list[BenchmarkDefinition]:
        return [b.definition for b in self._benchmarks.values()]
