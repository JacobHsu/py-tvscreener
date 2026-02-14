# Backtesting Instructions

This directory contains scripts for backtesting technical indicators against historical price data stored in the local SQLite database.

## Prerequisites

- Python 3.x
- Required packages: `pandas`, `sqlite3` (standard library)
- Local database file at `../data/history.db` containing `technical_indicators` table.

## Available Scripts

### 1. `backtest_dc_strategy.py`
**Purpose**: Run the "Donchian Channel Lower Band" specific strategy.
- **Rule**: Checks if the `donchian_lower` value at the session start is breahed by the session close price.
- **Run**:
  ```bash
  python backtesting/backtest_dc_strategy.py
  ```

### 2. `find_best_indicator.py`
**Purpose**: Analyze **ALL** available price-based indicators in the database to find the best support level.
- **Rule**: Checks win rate (Close >= Support) and calculates the "Safe Distance" to the intraday low.
- **Output**: A ranked list of indicators sorted by Win Rate and Tightest Support.
- **Run**:
  ```bash
  python backtesting/find_best_indicator.py
  ```

## Strategy Documentation
See `.agent/strategies/dc_backtest.md` for detailed rules and findings.
