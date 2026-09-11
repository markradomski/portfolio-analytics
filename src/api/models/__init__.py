"""Pydantic response models for the portfolio API (API contract hardening,
sec 3). One module per family, mirroring src/analytics/'s own layout so a
reviewer can find the model for a given service function without guessing.

These are serialisation contracts only -- no financial calculation lives
here. Every model is populated from data src/analytics/ or src/history/
already computed, converted to JSON-safe primitives by
src/api/serialize.py's to_json(), and validated (not recalculated) into the
shape declared below.
"""

from src.api.models.attribution import (AttributionCapitalAppreciation,
                                        AttributionCash, AttributionIncome,
                                        AttributionInvestmentReturn,
                                        AttributionPeriod, AttributionTree,
                                        SecurityAttributionRow)
from src.api.models.capabilities import AnalyticsCapabilities
from src.api.models.common import (ApiModel, Capability, DataCoverage,
                                    DecimalString, Metric, ReconciliationResult)
from src.api.models.contributions import (ContributionHistoryRow,
                                           ContributionSummary)
from src.api.models.gains import (GainAttribution, RealisedGainSummary,
                                  SecurityRealisedGain)
from src.api.models.growth import (CashFlowEvent, PortfolioGrowthPoint,
                                   PortfolioGrowthSummary,
                                   PortfolioValueReconciliationCheck)
from src.api.models.history import (ActivityRow, AttributionReconciliationPair,
                                    BestWorstPeriods, CalendarPerformanceRow,
                                    ExtremePeriod, HealthStatus, Milestone,
                                    RollingIncomeYieldPoint,
                                    RollingReturnPoint, RollingVolatilityPoint)
from src.api.models.holdings import (AllocationHistoryPoint, AllocationResult,
                                     ConcentrationSnapshot, HoldingRow,
                                     UnrealisedGainSnapshot)
from src.api.models.income import (IncomeGrowthRow, IncomeRow,
                                   IncomeYieldResponse)
from src.api.models.performance import (PerformanceMethodology,
                                        PerformanceOverview,
                                        PerformancePeriod, TwrrMethodology)
from src.api.models.portfolio import (PortfolioDailyPoint, PortfolioOverview,
                                      PortfolioState)
from src.api.models.risk import (BenchmarkComparison, DrawdownAnalytics,
                                 DrawdownEpisode, HighWaterMarkStatus,
                                 RiskMetrics)

__all__ = [
    "ActivityRow", "AllocationHistoryPoint", "AllocationResult",
    "AnalyticsCapabilities", "ApiModel", "AttributionCapitalAppreciation",
    "AttributionCash", "AttributionIncome", "AttributionInvestmentReturn",
    "AttributionPeriod", "AttributionReconciliationPair", "AttributionTree",
    "BenchmarkComparison", "BestWorstPeriods", "CalendarPerformanceRow",
    "Capability", "CashFlowEvent", "ConcentrationSnapshot", "ContributionHistoryRow", "DrawdownAnalytics",
    "ContributionSummary", "DataCoverage", "DecimalString", "DrawdownEpisode",
    "ExtremePeriod", "GainAttribution", "HealthStatus", "HighWaterMarkStatus",
    "HoldingRow", "IncomeGrowthRow", "IncomeRow", "IncomeYieldResponse",
    "Metric", "Milestone", "PerformanceMethodology", "PerformanceOverview",
    "PerformancePeriod", "PortfolioDailyPoint", "PortfolioGrowthPoint",
    "PortfolioGrowthSummary", "PortfolioOverview", "PortfolioState",
    "PortfolioValueReconciliationCheck", "RealisedGainSummary", "ReconciliationResult",
    "RiskMetrics", "RollingIncomeYieldPoint", "RollingReturnPoint",
    "RollingVolatilityPoint", "SecurityAttributionRow", "SecurityRealisedGain",
    "TwrrMethodology", "UnrealisedGainSnapshot",
]
