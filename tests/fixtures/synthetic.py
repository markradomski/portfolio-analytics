"""A synthetic quarterly statement.

Mirrors the real layout -- including the traps that broke earlier versions of
the parser -- with invented figures and invented personal details:

  * an identity block above the title, plus labelled PII lines
  * a holdings row whose product name wraps across three lines
  * a cash row whose description wraps around the numeric line
  * a withdrawal description containing an account number
  * a distribution row whose per-unit rate precedes the amount
  * a trade that has not settled yet

The portfolio identity balances exactly:
    1000 + 500 - 200 + 600 + 20 - 10 = 1910
"""

FAKE_NAME = "A N OTHER"
FAKE_ADDRESS_1 = "42 EXAMPLE STREET"
FAKE_ADDRESS_2 = "SOMEWHERE VIC 3000"
FAKE_ACCOUNT = "99999999"
FAKE_BSB = "999999"
FAKE_DESTINATION = "88888888"

PAGE_1 = [
    FAKE_NAME,
    FAKE_ADDRESS_1,
    FAKE_ADDRESS_2,
    "Vanguard Personal Investor Quarterly Statement",
    "Period ending 30 September 2024",
    f"Investor name: {FAKE_NAME}",
    f"Account number: {FAKE_ACCOUNT}",
    "Tax file number status: Supplied",
    "Account type: Individual",
    "Your portfolio summary",
    "Portfolio opening value as at 1 July 2024 $1,000.00",
    "Deposits into Vanguard Cash Account $500.00",
    "Withdrawals from Vanguard Cash Account -$200.00",
    "Assets transferred in $0.00",
    "Assets transferred out $0.00",
    "Change in investment value $600.00",
    "Income from your investments $20.00",
    "Withholding tax $0.00",
    "Direct fees and costs $10.00",
    "Portfolio closing value as at 30 September 2024 $1,910.00",
    "Return after withholding tax and fees $610.00",
]

PAGE_2 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Your portfolio valuation as at 30 September 2024",
    "Summary",
    "Investment type Value ($)",
    "Vanguard Cash Account 390.00",
    "ETFs 1,500.00",
    "Income on investments due not yet received 20.00",
    "Total cash and investment value 1,910.00",
    "Vanguard Cash Account",
    "Investment Value date Value ($)",
    "Vanguard Cash Account 30-Sep-24 390.00",
    "Total Vanguard Cash Account 390.00",
    "Exchange traded funds (ETFs)",
    "Market closing",
    "Code Investment product Quantity price ($) Price date Value ($)",
    # Wrapped product name: the code and numbers land on their own line.
    "Test Security Index",
    "TST 15.00 100.000 30-Sep-24 1,500.00",
    "ETF",
    "Total ETFs 1,500.00",
]

PAGE_3 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Your Vanguard Cash Account transaction details",
    f"BSB: {FAKE_BSB}",
    "Effective date Transaction description Debits ($) Credits ($) Balance ($)",
    "1-Jul-2024 Opening balance 100.00",
    "02-Jul-2024 Account Fee 10.00 90.00",
    "19-Jul-2024 DIV: TST.XASX.AU @ AUD 2.0000 20.00 110.00",
    # Description wraps entirely around the numeric row.
    "Off-System BSB Direct Entry Deposit",
    "20-Jul-2024 500.00 610.00",
    f"- {FAKE_DESTINATION}",
    "One-off Cash Withdrawal to",
    "25-Jul-2024 200.00 410.00",
    f"{FAKE_DESTINATION} on 25-Jul-2024",
    # Description wraps but leaves a fragment on the row itself.
    "Australian Equity Transaction fee for",
    "26-Jul-2024 Test Security Index 20.00 390.00",
    "ETF Buy",
    "30-Sep-2024 Closing balance 390.00",
]

PAGE_4 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Your investment transaction details",
    "Trade date Settlement date Investment product Transaction description "
    "Quantity Price ($) Brokerage fee ($) Currency Value ($)",
    "26-Jul-2024 30-Jul-2024 Test Security Index ETF(TST) Bought Test Security "
    "10.00 100.000 20.00 AUD 1,020.00",
    # Trades placed near period end report no settlement date.
    "28-Sep-2024 Not yet settled Test Security Index ETF(TST) Bought Test Security "
    "5.00 100.000 0.00 AUD 500.00",
    "Notes:",
]

PAGE_5 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Total fees and costs you paid for the period 01-Jul-2024 to 30-Sep-2024",
    "Fees and costs deducted directly from your account Amount ($)",
    "Brokerage Fee 20.00",
    "Account Fee 10.00",
]

QUARTERLY_STATEMENT = [PAGE_1, PAGE_2, PAGE_3, PAGE_4, PAGE_5]

MALFORMED = [[
    "Vanguard Personal Investor Quarterly Statement",
    "Period ending 30 September 2024",
    "Your portfolio valuation as at 30 September 2024",
    "Exchange traded funds (ETFs)",
    "BAD not-a-number also-bad 30-Sep-24 nonsense",
    "Your investment transaction details",
    "99-Xxx-2024 Not yet settled Broken(BAD) Bought 1.00 1.000 0.00 AUD 1.00",
]]


# --- annual tax report ------------------------------------------------------
#
# Covers FY2025 (1 July 2024 to 30 June 2025), the year the synthetic quarterly
# statement falls in, so the TST distribution recorded there can be matched.
#
# The payment date is deliberately one day out from the statement's, because the
# real reports disagree with the statements by a day or two and the matcher has
# to tolerate that.

TAX_PAGE_1 = [
    "Vanguard Personal Investor Annual Tax Report",
    "1 July 2024 to 30 June 2025",
    f"Investor name: {FAKE_NAME}",
    f"Account number: {FAKE_ACCOUNT}",
    "Account type: Individual",
    "Income",
    "Interest income $0.00 10L",
    "Dividends Amount Tax guide reference",
    "Unfranked amount $0.00 11S",
    "Franked amount (not inclusive of franking credits) $20.00 11T",
    "Australian dividend franking credits $8.57 11U",
    "Gross dividend income $28.57",
    "Total gross income $28.57",
    "Tax offsets Amount Tax guide reference",
    "Australian dividend franking credits $8.57 11U",
    "Trust franking credits $0.00 13Q",
    "Trust foreign income tax offsets $0.00 20O",
    "Total tax offsets $8.57",
    "Total net income received $20.00",
    "Account Fee $10.00 N/A",
    "Brokerage $20.00 N/A",
    "Total fees $30.00",
    "Total withholding tax $0.00",
    "Discounted capital gains $0.00 18",
    "CGT concession $0.00 18",
    "Total current year capital gains $0.00 18H",
    "Net capital gain3 $0.00 18A",
    "Net capital losses carried forward $0.00 18V",
]

TAX_PAGE_2 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Australian dividend income and tax information",
    "Unfranked dividend Franked dividend income Franking tax Total dividend",
    "Ex date Payment date Code Investment product income "
    "(not including franking tax credits) credits income",
    "05-Jul-2024 18-Jul-2024 TST Test Security $0.00 $20.00 $8.57 $28.57",
    "Total Australian dividend income $0.00 $20.00 $8.57 $28.57",
]

TAX_PAGE_3 = [
    f"Account number: {FAKE_ACCOUNT}",
    "Australian trust distribution income and tax information",
    "Australian income",
    "Code Investment product credits) Unfranked amounts Franking tax credits "
    "Interest income Other deductions",
    "Test Security Index",
    "TST $0.00 $0.00 $0.00 $0.00 $0.00",
    "ETF",
    "Total Australian trust distributions $0.00 $0.00 $0.00 $0.00 $0.00",
]

TAX_REPORT = [TAX_PAGE_1, TAX_PAGE_2, TAX_PAGE_3]
