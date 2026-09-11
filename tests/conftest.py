import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.fixtures import synthetic          # noqa: E402
from tests.fixtures.pdf_builder import build_pdf   # noqa: E402


@pytest.fixture
def statement_dir(tmp_path):
    """A directory holding one synthetic quarterly statement PDF."""
    build_pdf(tmp_path / "2024-10-01_Quarterly_Statement_1.pdf",
              synthetic.QUARTERLY_STATEMENT)
    return tmp_path


@pytest.fixture
def statement_pdf(statement_dir):
    return next(statement_dir.glob("*.pdf"))


@pytest.fixture
def tax_dir(statement_dir):
    """A statement plus the annual tax report covering the same year."""
    build_pdf(statement_dir / "2025-08-01_Annual_Tax_Report_2.pdf",
              synthetic.TAX_REPORT)
    return statement_dir


@pytest.fixture
def tax_pdf(tax_dir):
    return tax_dir / "2025-08-01_Annual_Tax_Report_2.pdf"


# --- engine helpers ---------------------------------------------------------

from datetime import date as _date          # noqa: E402
from decimal import Decimal as _D           # noqa: E402

from src.engine.ledger import Event         # noqa: E402
from src.engine.prices import PriceQuality, Quote   # noqa: E402
from src.models import TxnType              # noqa: E402


def ev(day, kind, *, code=None, units=None, price=None, net=None, fees=None,
       gross=None, settle=None, eid=None, description=""):
    """Build a ledger event without going through a PDF."""
    return Event(
        event_id=eid or f"{day}-{kind.value}-{code or ''}-{net or units or ''}",
        trade_date=day,
        settlement_date=settle,
        type=kind,
        security_id=code,
        code=code,
        units=_D(str(units)) if units is not None else None,
        price=_D(str(price)) if price is not None else None,
        gross_amount=_D(str(gross)) if gross is not None else None,
        fees=_D(str(fees)) if fees is not None else None,
        net_amount=_D(str(net)) if net is not None else None,
        description=description or kind.value,
    )


class StubPrices:
    """Fixed prices per security per date, with carry-forward like the real one."""

    def __init__(self, prices):
        self._prices = {k: sorted(v.items()) for k, v in prices.items()}

    def quote(self, security_id, on):
        series = self._prices.get(security_id)
        if not series:
            return Quote(None, PriceQuality.UNAVAILABLE, None)
        usable = [(d, p) for d, p in series if d <= on]
        if not usable:
            return Quote(None, PriceQuality.UNAVAILABLE, None)
        as_at, price = usable[-1]
        return Quote(price, PriceQuality.QUOTED if as_at == on
                     else PriceQuality.CARRIED_FORWARD, as_at)


@pytest.fixture
def prices():
    return StubPrices
