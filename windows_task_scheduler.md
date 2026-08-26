# Windows Task Scheduler

The local scheduler can run `run_cycle_and_log.bat` on trading days at 09:40 and 15:45 Eastern Time. It should remain in preview mode until credentials, permissions, data quality, assignment behavior, and emergency shutdown procedures are tested.

Typical setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows_tasks.ps1
```

Expected task names:

- `QQQ-TQQQ-Autotrade-0940`
- `QQQ-TQQQ-Autotrade-1545`

Runtime logs belong in the ignored local `logs/` directory and must not be committed.

