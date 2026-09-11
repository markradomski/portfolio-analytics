from decimal import Decimal as D

from src.engine.attribution import Attribution, Contribution

ZERO = D("0")


def _c(code, realised=0, unrealised=0, income=0, fees=0):
    return Contribution(security_id=code, code=code, realised_gain=D(str(realised)),
                        unrealised_gain=D(str(unrealised)), income=D(str(income)),
                        fees=D(str(fees)))


def test_profit_combines_every_source():
    c = _c("AAA", realised=100, unrealised=50, income=25, fees=5)
    assert c.profit == D("170")


def test_contributions_sum_exactly_to_the_total():
    """A profit-share attribution has no residual by construction."""
    attribution = Attribution(
        contributions=[_c("AAA", realised=1000), _c("BBB", unrealised=-400),
                       _c("Cash", income=50, fees=30)],
        average_capital=D("10000"))
    parts = sum((c.contribution_pct(attribution.average_capital)
                 for c in attribution.contributions), ZERO)
    assert parts == attribution.total_pct
    assert attribution.total_profit == D("620")


def test_losses_rank_below_gains():
    attribution = Attribution(
        contributions=[_c("LOSS", realised=-500), _c("WIN", realised=900)],
        average_capital=D("1000"))
    assert [c.code for c in attribution.ranked()] == ["WIN", "LOSS"]


def test_no_capital_gives_no_percentage_rather_than_dividing_by_zero():
    attribution = Attribution(contributions=[_c("AAA", realised=10)],
                              average_capital=ZERO)
    assert attribution.total_pct is None
    assert attribution.contributions[0].contribution_pct(ZERO) is None
