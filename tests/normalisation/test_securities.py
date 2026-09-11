import pytest

from src.models import SecurityType
from src.normalisation.securities import normalise_code, security_type_for


@pytest.mark.parametrize("raw,expected", [
    ("VAS.AX", "VAS"),
    ("WTC.XASX.AU", "WTC"),
    ("VAS", "VAS"),
    ("vas", "VAS"),
    (" VGAD ", "VGAD"),
])
def test_strips_exchange_suffixes(raw, expected):
    assert normalise_code(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "  ", "..."])
def test_unusable_codes_return_none(raw):
    assert normalise_code(raw) is None


def test_type_prefers_statement_section_over_name():
    assert security_type_for("etf", "Anything") is SecurityType.ETF
    assert security_type_for("australian_share", "Vanguard ETF") is SecurityType.SHARE


def test_type_falls_back_to_name():
    assert security_type_for(None, "Vanguard Australian Shares Index ETF") is SecurityType.ETF
    assert security_type_for(None, "Some Managed Fund") is SecurityType.MANAGED_FUND
    assert security_type_for(None, "BHP Billiton Limited") is SecurityType.SHARE
