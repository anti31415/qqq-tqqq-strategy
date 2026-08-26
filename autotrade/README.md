# Autotrade Scaffold

这是这套 `QQQ / TQQQ` 策略的自动化交易工程骨架。

当前阶段目标：

- 先打通 `Alpaca paper`
- 再补 `IBKR paper`
- 默认只做“预览订单”，不直接发单

## 快速开始

1. 复制 `.env.example` 为 `.env`
2. 填入 `Alpaca paper` API key
3. 如果要检测 `IBKR`，先本地启动 `Client Portal Gateway`
4. 运行：

```powershell
& 'C:\Users\antiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m autotrade.cli doctor
```

## 常用命令

```powershell
# 检查配置与 broker 连通性
python -m autotrade.cli doctor

# 查看 Alpaca 账户摘要
python -m autotrade.cli alpaca-account

# 计算最新信号
python -m autotrade.cli signal

# 预览下一笔 CSP 候选
python -m autotrade.cli preview-csp

# 自动判断今天应该做什么
python -m autotrade.cli plan

# 运行一次完整检查并自动写日志
python -m autotrade.cli plan --place-order

# 本地常驻调度，按时自动检查并写日志
python -m autotrade.cli schedule --times 09:40,15:45

# 真正向 Alpaca paper 发单
python -m autotrade.cli preview-csp --place-order
```

## 当前实现边界

- 已实现：
  - 配置加载
  - Alpaca paper 账户连通
  - QQQ 趋势/RSI/阴线信号
  - TQQQ Put 候选筛选
  - 持仓感知的动作决策：`卖 Put / 卖 Covered Call / 不操作`
  - 订单 payload 预览
  - Alpaca paper 下单
- 每次执行写入 `logs/*.jsonl`
  - 每次执行追加写入单一历史日志：
    - `logs/autotrade_history.jsonl`
    - `logs/autotrade_history.txt`
  - 成功提交 paper 订单后可通过本地 SMTP 发邮件
  - 本地常驻调度脚本
  - IBKR Client Portal Gateway 连通性检查

- 暂未实现：
  - 自动 assignment / covered call 状态机
  - 多 broker 统一持仓同步
  - 告警

## 参考文档

- [06_API与启动清单.md](../06_API与启动清单.md)
- [07_指标公式与自动执行流程.md](../07_指标公式与自动执行流程.md)
