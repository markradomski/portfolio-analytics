"""Portfolio vs benchmark comparison (sec 21-23).

No benchmark is hard-coded, and none is loaded by default: this codebase has
never integrated an external price feed (deferred since Phase 2's own
scaffolding), so every comparison here reports UNAVAILABLE until a caller
registers one via BenchmarkRegistry. That is the correct default, not a
placeholder to be embarrassed about -- fabricating a benchmark return with no
real price data would be worse than admitting there isn't one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.result import DataQuality, Metric, unavailable
from src.engine.benchmark import Benchmark, BenchmarkRegistry
from src.engine.returns import time_weighted_return
from src.history.periods import PerformancePeriod

ZERO = Decimal("0")


@dataclass(frozen=True)
class BenchmarkComparison:
    portfolio_return: Decimal | None
    benchmark_return: Decimal | None
    relative_return: Decimal | None
    portfolio_methodology: str
    benchmark_methodology: str | None
    methodology_mismatch: bool
    status: str
    note: str | None = None
    # Identifying detail (hardening sec 11): what benchmark this actually
    # was, not just that one existed, so a UI can label the comparison
    # correctly and a caller can audit which source/frequency backed it.
    benchmark_id: str | None = None
    benchmark_name: str | None = None
    benchmark_return_method: str | None = None
    benchmark_data_source: str | None = None
    benchmark_frequency: str | None = None
    benchmark_coverage: int | None = None   # paired observations actually used


def compare_to_benchmark(portfolio_period: PerformancePeriod,
                         registry: BenchmarkRegistry, benchmark_id: str,
                         dates: list[date]) -> BenchmarkComparison:
    """Compares a portfolio period return (TWRR -- the methodology comparable
    to a benchmark, since it neutralises the portfolio's own flow timing)
    against a registered benchmark's return over the same dates.

    Flags, rather than silently proceeding, when the benchmark's own
    return_methodology is price_return: comparing that against the
    portfolio's total return (which includes reinvested income) understates
    the portfolio's real outperformance (sec 23).
    """
    benchmark = registry.get(benchmark_id)
    if benchmark is None:
        return BenchmarkComparison(
            portfolio_period.twrr, None, None, "TWRR", None, False,
            "UNAVAILABLE", f"no benchmark registered under '{benchmark_id}'",
            benchmark_id=benchmark_id)

    detail = dict(
        benchmark_id=benchmark.definition.identifier,
        benchmark_name=benchmark.definition.name,
        benchmark_return_method=benchmark.definition.return_methodology,
        benchmark_data_source=benchmark.definition.price_source,
        benchmark_frequency="irregular (per registered price series)")

    if portfolio_period.twrr is None:
        return BenchmarkComparison(
            None, None, None, "TWRR", benchmark.definition.return_methodology,
            False, "UNAVAILABLE",
            "portfolio TWRR is unavailable for this period -- see the"
            " period's own status/note", **detail)

    period_returns = benchmark.return_series(dates)
    measurable = [r for r in period_returns if r is not None]
    if not measurable:
        return BenchmarkComparison(
            portfolio_period.twrr, None, None, "TWRR",
            benchmark.definition.return_methodology, False, "UNAVAILABLE",
            f"'{benchmark_id}' has no return data over this period",
            **detail, benchmark_coverage=0)

    compound = Decimal(1)
    for r in measurable:
        compound *= (Decimal(1) + r)
    benchmark_return = compound - Decimal(1)

    mismatch = benchmark.definition.return_methodology == "price_return"
    note = None
    if mismatch:
        note = (f"'{benchmark_id}' is a PRICE return (dividends excluded);"
                " the portfolio figure is a TOTAL return (income included)."
                " This comparison understates portfolio outperformance --"
                " see docs/analytics.md 'Benchmark caveats'.")

    return BenchmarkComparison(
        portfolio_return=portfolio_period.twrr, benchmark_return=benchmark_return,
        relative_return=portfolio_period.twrr - benchmark_return,
        portfolio_methodology="TWRR (total return)",
        benchmark_methodology=benchmark.definition.return_methodology,
        methodology_mismatch=mismatch, status="OK", note=note,
        **detail, benchmark_coverage=len(measurable))
