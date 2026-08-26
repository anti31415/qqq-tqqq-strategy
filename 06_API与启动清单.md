# API 与启动清单

这份清单按我们约定的顺序来：先 `Alpaca paper`，再 `IBKR paper`。

## 1. Alpaca：你现在需要做什么

### 1.1 获取 paper API key

位置：

- 登录 Alpaca 控制台
- 打开交易/开发者后台
- 生成 `paper` 专用 API key / secret

官方文档：

- [Authentication](https://docs.alpaca.markets/docs/api-references/trading-api/)

注意：

- `paper` 和 `live` 是不同域名、不同凭证
- `paper` 域名：`https://paper-api.alpaca.markets`
- `live` 域名：`https://api.alpaca.markets`

### 1.2 确认期权等级

对这套策略，至少要支持：

- `Sell cash-secured put`
- `Sell covered call`

官方文档里这属于 `Level 1`：

- [Options Trading Overview](https://docs.alpaca.markets/docs/options-trading-overview)

### 1.3 决定是否升级数据计划

默认免费 `Basic`：

- 股票实时只含 `IEX`
- 期权实时只含 `indicative feed`

如果你想更接近真实 paper 调试体验，建议升级：

- `Algo Trader Plus`：`$99/月`
- 包含股票全市场和期权 `OPRA` 实时数据

官方文档：

- [About Market Data API](https://docs.alpaca.markets/docs/about-market-data-api)

### 1.4 Alpaca 费用怎么理解

- API 本身没有额外接入费
- 对 retail 通过 API 交易股票/ETF/期权，官方写的是 `commission-free`
- 但仍可能有监管费等非佣金费用

官方资料：

- [Alpaca Options](https://alpaca.markets/options)
- [Trading API](https://docs.alpaca.markets/docs/trading-api)

## 2. IBKR：你现在需要做什么

### 2.1 确认已有 paper account

官方说明：

- 大多数已开通并注资的账户都可配套 paper account

文档：

- [IBKR Paper Trading Account](https://ibkrcampus.com/campus/glossary-terms/paper-trading-account/)

### 2.2 找到 paper 用户名

位置：

- 登录 `Client Portal`
- 右上角头像
- `Settings`
- `Paper Trading Account`

这里可以看到：

- `Paper Trading Username`
- `Paper Trading Account Number`

文档：

- [Client Portal API paper auth](https://ibkrcampus.com/campus/ibkr-api-page/cpapi-v1/)

### 2.3 选择接入方式

我建议先用：

- `Client Portal Gateway` 做连通性检查

后续如果要做更完整、更稳定的策略执行，再补：

- `IB Gateway + TWS API`

### 2.4 如果后面走 TWS / IB Gateway

至少要在设置里确认：

- Enable `ActiveX and Socket Clients`
- Disable `Read-Only API`
- 确认 `Socket Port`

文档：

- [TWS API Documentation](https://ibkrcampus.com/campus/ibkr-api-page/trader-workstation-api/)

### 2.5 IB 费用怎么理解

- API 本身官方写的是 `free of cost`
- 但交易仍按券商费率收费
- 美国股票/ETF：
  - `IBKR Lite` 合资格订单可免佣
  - `IBKR Pro` 通常按每股收费
- 美国期权：
  - 大致 `USD 0.15 - 0.65 / contract`
  - 另有交易所、清算、监管费用

文档：

- [IBKR Web API Trading](https://ibkrcampus.com/campus/ibkr-api-page/web-api-trading/)
- [IBKR Commissions](https://www.interactivebrokers.com/en/pricing/commissions-home.php)
- [IBKR Options Commissions](https://www.interactivebrokers.com/en/pricing/commissions-options.php)

## 3. 本地代码怎么配置

在这个目录：

- `autotrade/.env.example`

复制为：

- `autotrade/.env`

然后至少填：

```env
ALPACA_API_KEY_ID=...
ALPACA_API_SECRET_KEY=...
ALPACA_API_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_BASE_URL=https://data.alpaca.markets
IBKR_GATEWAY_BASE_URL=https://localhost:5000/v1/api
DRY_RUN=true
```

## 4. 第一步先跑哪个命令

进入目录后，先跑：

```powershell
& 'C:\Users\antiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m autotrade.cli doctor
```

然后依次跑：

```powershell
& 'C:\Users\antiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m autotrade.cli alpaca-account

& 'C:\Users\antiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m autotrade.cli signal

& 'C:\Users\antiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m autotrade.cli plan
```

## 5. 当前这版代码已经能做什么

- 检查 Alpaca paper credentials 是否可用
- 读取 Alpaca paper 账户
- 读取最新 `QQQ` 日线并计算：
  - `SMA200`
  - `RSI(14)`
  - 当天是否收阴
- 根据持仓和信号自动判断：
  - 卖 `cash-secured put`
  - 卖 `covered call`
  - 或者继续等待
- 检查 `IBKR Client Portal Gateway` 是否已登录

## 6. 下一步我会继续做什么

等你把 `.env` 填好后，我下一步建议继续补：

1. Alpaca paper 真正下单
2. 订单状态轮询与成交跟踪
3. assignment / expiry 检测
4. 持有正股后的 `covered call` 自动预览
5. IB broker adapter 的下单与持仓查询
