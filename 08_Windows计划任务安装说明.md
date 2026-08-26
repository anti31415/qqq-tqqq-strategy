# Windows 计划任务安装说明

目标：

- 工作日 `09:40` 运行一次
- 工作日 `15:45` 再运行一次
- 运行脚本：`run_cycle_and_log.bat`
- 每次检查自动写：
  - `logs/autotrade_history.jsonl`
  - `logs/autotrade_history.txt`

## 最简单的执行方式

### 第 1 步

打开 PowerShell，进入目录：

```powershell
cd "C:\Users\antiz\OneDrive\Desktop\Codex\量化研究\tianbro_qqq_tqqq_strategy\autotrade"
```

### 第 2 步

执行安装脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows_tasks.ps1
```

### 第 3 步

看到下面两条任务名，就表示安装成功：

- `QQQ-TQQQ-Autotrade-0940`
- `QQQ-TQQQ-Autotrade-1545`

## 任务具体做什么

两条任务都会执行：

```text
run_cycle_and_log.bat
```

这个脚本会：

1. 调用 Alpaca API
2. 获取 `QQQ/TQQQ` 数据
3. 计算 `SMA200`、`RSI(14)`、是否收阴
4. 判断：
   - `sell_cash_secured_put`
   - `sell_covered_call`
   - `hold`
5. 如果条件满足且允许下单，就发 paper order
6. 把结果写到 `jsonl` 和 `txt` 日志
7. 如果成功提交了 paper order，且你已经配置了 SMTP，就发送邮件通知

## 如何检查是否运行成功

看这里：

- `C:\Users\antiz\OneDrive\Desktop\Codex\量化研究\tianbro_qqq_tqqq_strategy\autotrade\logs`

重点看：

- `autotrade_history.txt`

这个文件最适合人工检查。

## 如何启用本地邮件通知

编辑：

- `autotrade\.env`

把这些项填好：

```env
NOTIFY_EMAIL_TO=your_destination_email@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USERNAME=你的发件邮箱
SMTP_PASSWORD=你的 SMTP 密码或 Gmail App Password
SMTP_FROM=你的发件邮箱
```

说明：

- 只有在“成功提交 paper 订单”时才会发邮件
- 没有配置 SMTP 不会影响交易检查，只会在日志里写明 `smtp_not_configured`

## 如何手动测试一次

在同一个目录直接运行：

```powershell
cmd /c .\run_cycle_and_log.bat
```

跑完以后去 `logs` 目录看 `autotrade_history.txt`。

## 如何删除计划任务

管理员 PowerShell 或普通 PowerShell 都可以，执行：

```powershell
Unregister-ScheduledTask -TaskName "QQQ-TQQQ-Autotrade-0940" -Confirm:$false
Unregister-ScheduledTask -TaskName "QQQ-TQQQ-Autotrade-1545" -Confirm:$false
```

## 当前已停用的旧自动化

Codex 内部的自动任务已经删除：

- `morning-paper-check`
- `close-paper-check`

现在建议只保留本地 Windows 计划任务，避免重复执行。
