# Backtest Results

## Method

- Price source: Yahoo Finance daily data.
- Main window: `2012-01-01` through `2025-12-31`.
- Signal: QQQ above SMA200, RSI(14) below 50, and a down day.
- Option approximation: 33 DTE contracts, Black–Scholes pricing, historical volatility, and simplified strike selection.
- Stage 1: $20,000 initial capital plus $1,500 monthly contributions.
- Stage 2: $100,000 initial capital plus $1,500 monthly contributions.

## Stage 1 summary

| Metric | Value |
| --- | ---: |
| Date reaching $100,000 | 2016-05-02 |
| Days elapsed | 1,583 |
| Cumulative contributions at milestone | $99,500 |
| Equity at milestone | $100,537.42 |
| Wheel cycles | 37 |
| Put assignments | 12 |
| Trend-break exits | 3 |
| Maximum drawdown | -21.63% |
| Ending equity | $276,547.64 |

The milestone is driven primarily by continued contributions and avoiding catastrophic loss, not by a claim of extraordinary wheel returns.

