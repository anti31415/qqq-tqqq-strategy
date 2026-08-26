# Broker Evaluation

The automation target is US ETF trading, option-chain access, cash-secured puts, covered calls, position tracking, assignment handling, and paper/live separation.

## Research shortlist

| Broker | Strength | Main trade-off |
| --- | --- | --- |
| Interactive Brokers | Broad products, strong order coverage, paper trading | More complex integration and operations |
| Tradier | Simple API and clear options workflow | Sandbox data and streaming limitations |
| Alpaca | Good developer experience and paper workflow | Lighter options ecosystem and newer coverage |

The current scaffold starts with Alpaca paper trading and includes an IBKR gateway adapter. Broker permissions, margin treatment, assignment, order validation, and market-data entitlements must be tested separately.

