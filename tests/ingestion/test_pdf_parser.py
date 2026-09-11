from src.ingestion.pdf_parser import load, redact_inline, strip_pii
from tests.fixtures import synthetic


def test_strips_address_block_above_the_title():
    pages = strip_pii(["\n".join(synthetic.PAGE_1)])
    assert synthetic.FAKE_NAME not in pages[0]
    assert synthetic.FAKE_ADDRESS_1 not in pages[0]
    assert synthetic.FAKE_ADDRESS_2 not in pages[0]
    assert "Vanguard Personal Investor Quarterly Statement" in pages[0]


def test_strips_labelled_identity_lines_on_every_page():
    pages = strip_pii(["\n".join(synthetic.PAGE_1), "\n".join(synthetic.PAGE_3)])
    joined = "\n".join(pages)
    assert "Investor name" not in joined
    assert "Account number" not in joined
    assert "Tax file number" not in joined
    assert "BSB:" not in joined
    assert synthetic.FAKE_ACCOUNT not in joined
    assert synthetic.FAKE_BSB not in joined


def test_keeps_bsb_appearing_inside_a_transaction_description():
    """Only the labelled BSB line is identity; 'Off-System BSB Direct Entry
    Deposit' is a payment method and must survive."""
    pages = strip_pii(["\n".join(synthetic.PAGE_3)])
    assert "Off-System BSB Direct Entry Deposit" in pages[0]


def test_keeps_the_financial_content():
    pages = strip_pii(["\n".join(synthetic.PAGE_1)])
    assert "Portfolio closing value" in pages[0]
    assert "$1,910.00" in pages[0]


def test_redacts_identifiers_inside_free_text():
    assert redact_inline("One-off Cash Withdrawal to 13257353 on 29-Apr-2024") == \
        "One-off Cash Withdrawal to [redacted] on 29-Apr-2024"


def test_short_numbers_survive_redaction():
    """Amounts and unit counts must not be mistaken for identifiers."""
    assert redact_inline("DIV: VAS @ AUD 0.8479") == "DIV: VAS @ AUD 0.8479"
    assert redact_inline("Buy 12345 units") == "Buy 12345 units"


def test_lines_carry_their_page_number(statement_pdf):
    lines, page_count = load(statement_pdf)
    assert page_count == 5
    valuation = next(l for l in lines if "portfolio valuation as at" in l.text)
    assert valuation.page == 2
    cash = next(l for l in lines if "Cash Account transaction details" in l.text)
    assert cash.page == 3
