# QQQ / TQQQ Strategy Research

An open research project for a QQQ-signal and TQQQ-execution framework. It includes an approximate backtest, stage-based portfolio research, and a paper-trading scaffold.

## Contents

- `strategy_rules.md` — asset roles and stage definitions.
- `backtest_results.md` — assumptions, results, and limitations.
- `performance_comparison.md` — benchmark comparison.
- `broker_evaluation.md` — broker and automation considerations.
- `indicators_and_execution.md` — formulas and decision flow.
- `api_and_setup.md` — configuration and setup checklist.
- `windows_task_scheduler.md` — local scheduling guide.
- `autotrade/` — Alpaca paper / IBKR gateway scaffold.
- `research_outputs/` — generated equity curves, summaries, and trade records.

## Reproducibility

The source material is an informal strategy description, so several details require explicit assumptions. Results are approximate research outputs, not a live-account reconstruction or a performance promise. Review transaction costs, assignment, margin, slippage, leverage decay, and out-of-sample behavior before using any result.

## Quick start

```powershell
node backtest_tianbro_qqq_tqqq.js
```

The paper-trading scaffold is preview-first. Never commit `.env`, account state, or runtime logs.

## Contribution and risk

See `CONTRIBUTING.md` for reproducibility requirements. TQQQ, options, and margin can create substantial losses. This repository is for education and research only and is not investment advice.

