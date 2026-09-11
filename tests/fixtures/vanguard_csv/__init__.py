"""Small synthetic Vanguard CSV fixtures for Step 9B.

NOT the user's real exports. Every account-like number here is a made-up
placeholder (`99999999`, `12345678`) chosen so the privacy tests can assert it
never survives. Securities and amounts are illustrative.
"""

from __future__ import annotations

# --- investment transactions CSV ------------------------------------------

INVESTMENT_HEADER = (
    "Account number,Investment,Product ID,Product Type,Trade Date,Type,"
    "Unit Price,Quantity,Value,Brokerage"
)

INVESTMENT_ROWS = [
    # blank brokerage (early ETF buy) -> canonical 0.00
    "99999999,Vanguard Australian Shares Index ETF,VAS,ETF,18-Sep-2020,Buy Trade,75.83,14,1061.62,",
    # explicit $9 brokerage on a later share buy
    "99999999,BHP Billiton Limited,BHP,Share,03-Feb-2025,Buy Trade,46.31,22,1018.82,9",
    # sell with negative quantity + $9 brokerage
    "99999999,Rio Tinto Limited,RIO,Share,01-May-2026,Sell trade,172.47,-9,1552.23,9",
    # ETF sell, blank brokerage
    "99999999,Vanguard International Shares Index ETF,VGS,ETF,12-Mar-2026,Sell trade,110.00,-5,550.00,",
]

INVESTMENT_CSV = INVESTMENT_HEADER + "\n" + "\n".join(INVESTMENT_ROWS) + "\n"

# A row whose Value is materially inconsistent with quantity*price.
INVESTMENT_CSV_BAD_ARITHMETIC = (
    INVESTMENT_HEADER + "\n"
    "99999999,Vanguard Australian Shares Index ETF,VAS,ETF,18-Sep-2020,Buy Trade,75.83,14,9999.99,\n"
)

# Malformed rows: unknown type, unparseable date, zero quantity, sign mismatch.
INVESTMENT_CSV_MALFORMED = (
    INVESTMENT_HEADER + "\n"
    "99999999,Good ETF,VAS,ETF,18-Sep-2020,Buy Trade,75.83,14,1061.62,\n"
    "99999999,Bad Type,VAS,ETF,18-Sep-2020,Rollover,75.83,14,1061.62,\n"
    "99999999,Bad Date,VAS,ETF,not-a-date,Buy Trade,75.83,14,1061.62,\n"
    "99999999,Zero Qty,VAS,ETF,18-Sep-2020,Buy Trade,75.83,0,0.00,\n"
    "99999999,Sign Mismatch,VAS,ETF,18-Sep-2020,Buy Trade,75.83,-14,1061.62,\n"
)


# --- cash transactions CSV ----------------------------------------------------

CASH_HEADER = "Date,Type,Product Type,Product Name,Product ID,Units,Total"

CASH_ROWS = [
    # deposit with a destination-reference number in the description
    "11-Sep-2020,Deposit,Cash account,Off-System BSB Direct Entry Deposit - 12345678,CASH,,10000",
    # a bank name / initials suffix -- alphabetic, so digit-redaction alone
    # would leave it exposed; the deposit-specific stripping must catch it
    "16-Sep-2020,Deposit,Cash account,Off-System BSB Direct Entry Deposit - demobank,CASH,,5000",
    "17-Sep-2020,Deposit,Cash account,Off-System BSB Direct Entry Deposit - XJQ,CASH,,100",
    # withdrawal to another account (account number in the description)
    "06-May-2026,Withdrawal,Cash account,One-off Cash Withdrawal to 99999999 on 05-May-2026,CASH,,-3400",
    # admin fee
    "02-Jul-2026,Fees and Charges,Cash account,OngoingAdminChargeByValue,CASH,,-0.28",
    # interest
    "30-Sep-2020,Interest,Cash account,Cash Account Interest,CASH,,0.86",
    # distribution identified by security NAME only (blank Product ID)
    "15-Jul-2021,Distribution,ETF,Vanguard Australian Shares Index ETF,,,120.50",
    # distribution for a listed company (share) -> canonical DIVIDEND in Stage 3
    "20-Mar-2025,Distribution,Share,BHP Billiton Limited,BHP,,33.04",
    # cash leg of the VAS buy above
    "18-Sep-2020,Buy,ETF,Vanguard Australian Shares Index ETF,VAS,14,-1061.62",
    # cash leg of the RIO sell above
    "01-May-2026,Sell,Share,Rio Tinto Limited,RIO,-9,1552.23",
    # brokerage cash leg of the RIO sell ($9, settles 2 days later)
    "03-May-2026,Fees and Charges,Cash account,Australian Equity Transaction fee for Rio Tinto Limited Sell,RIO,,-9",
    # brokerage cash leg of the BHP buy
    "05-Feb-2025,Fees and Charges,Cash account,Australian Equity Transaction fee for BHP Billiton Limited Buy,BHP,,-9",
    # quarterly admin fee
    "02-Oct-2021,Fees and Charges,Cash account,OngoingAdminChargeByValue,CASH,,-9.31",
    # explicit reversal of that admin fee, a few weeks later (+ sign, kept)
    "25-Oct-2021,Fees and Charges,Cash account,Reversal: OngoingAdminChargeByValue,CASH,,9.31",
]

CASH_CSV = CASH_HEADER + "\n" + "\n".join(CASH_ROWS) + "\n"

CASH_CSV_MALFORMED = (
    CASH_HEADER + "\n"
    "11-Sep-2020,Deposit,Cash account,Good Deposit,CASH,,10000\n"
    "11-Sep-2020,Rebate,Cash account,Unknown Type,CASH,,5.00\n"
    "not-a-date,Interest,Cash account,Cash Account Interest,CASH,,0.86\n"
    "11-Sep-2020,Withdrawal,Cash account,Bad Total,CASH,,not-a-number\n"
)

# A withdrawal exported with a positive Total -- a sign anomaly to warn on.
CASH_CSV_SIGN_ANOMALY = (
    CASH_HEADER + "\n"
    "06-May-2026,Withdrawal,Cash account,Reversed withdrawal,CASH,,3400\n"
)
