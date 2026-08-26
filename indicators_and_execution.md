# Indicators and Execution Flow

## Indicators

```text
SMA200(t) = mean of the latest 200 QQQ closes
RSI(14)   = 100 - 100 / (1 + AvgGain / AvgLoss)
DownDay   = QQQ close[t] < QQQ close[t-1]
```

## Decision flow

Open a new cash-secured put only when QQQ is above SMA200, RSI(14) is below 50, the day is negative, and no conflicting position requires action. If assignment occurs, evaluate covered-call management. If the trend breaks, prioritize risk reduction over mechanically holding leveraged exposure.

All decisions should be logged with signal values, candidate contract, order preview, broker response, and whether the result was simulated or submitted.

