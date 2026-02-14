---
description: Long-term backtesting strategy for Technical Indicators as daily support
---

# Support Indicator Backtest (DC Lower vs Pivot Points)

## Objective
To identify the technical indicator that serves as the most reliable, non-breached support price.
Initially, we tested **Donchian Channel Lower Band (DC Lower)**, but it failed on 2026-02-10.
We are now comparing multiple indicators to find the one that:
1.  **100% Win Rate**: Never breached at Session Close.
2.  **Closest to Target**: The support level is closest to the actual Intraday Low (Tightest Support).

## Time Interval Definition (Taiwan Time)
- **Cycle**: Daily
- **Start**: 16:00 Taiwan Time (UTC 08:00)
- **End**: Next Day 16:00 Taiwan Time (UTC 08:00)

## Breach Definition
- **Baseline**: The Indicator value recorded at the **START** of the session (16:00 TW).
- **Comparison**: The `Close` price recorded at the **END** of the session (Next Day 16:00 TW).
- **Rule**:
    - **PASS**: Final Close Price >= Start Indicator Value
    - **FAIL**: Final Close Price < Start Indicator Value

## Current Best Indicator
Based on backtesting (Feb 10 - Feb 14, 2026):
- **Pivot Fibonacci S1** (`pivot_fib_s1`)
    - **Win Rate**: 100% (Passed all sessions)
    - **Type**: Static (Pre-calculated). Less dynamic but currently the safest tight support.

- **Donchian Channel Lower** (`donchian_lower`)
    - **Win Rate**: 67% (Failed on big drop day).
    - **Type**: Dynamic. More responsive but can be breached in strong trends.

## How to Run locally

### 1. Test DC Lower (Original Strategy)
```bash
python backtesting/backtest_dc_strategy.py
```

### 2. Compare All Indicators (New Analysis)
Run this script to analyze multiple indicators (Pivot, BB, EMA, etc.) and find the best performer:
```bash
python backtesting/find_best_indicator.py
```
