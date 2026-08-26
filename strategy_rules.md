# Strategy Rules

## Asset roles

- QQQ: signal and trend reference.
- TQQQ: high-volatility execution vehicle for the wheel research.
- QQQM or QQQ: long-term core allocation.
- QQQ LEAPS: optional upside accelerator in the larger-account stage.

## Stage 1: cash-secured put wheel

The modeled entry requires QQQ above its 200-day moving average, RSI(14) below 50, and a down day. The example contract uses approximately 33 DTE and an out-of-the-money TQQQ put. After assignment, the model may sell a covered call; if QQQ breaks its long-term trend, the framework prioritizes risk reduction.

## Stage 2: diversified growth portfolio

The modeled allocation is 50% core QQQ/QQQM exposure, 10% cash, 32% TQQQ wheel exposure, and 8% QQQ LEAPS exposure, with monthly contributions. This is a research allocation, not a universal recommendation.

## Open questions

Future work should test position sizing, assignment handling, margin rules, implied-volatility selection, transaction costs, leverage decay, stress periods, and walk-forward validation.

