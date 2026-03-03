"""
校準 DC Lower - k * ATR(14) 的最佳 k 值

評分標準：
  - 支撐位低於 DC Lower（有意義）
  - 24H 內價格「接近」（最低價在支撐位上方 0~2%）但不跌破
  - 越多天符合越好

輸出：各 k 值的接近率、跌破率、守住率
"""
import sqlite3
import pandas as pd
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"

conn = sqlite3.connect(DB_PATH)
rows = {}
for sym in ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]:
    df = pd.read_sql_query(
        "SELECT collected_at, price, low, donchian_lower, atr_14 "
        "FROM technical_indicators WHERE symbol=? ORDER BY collected_at",
        conn, params=(sym,),
    )
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True).dt.tz_convert("Asia/Taipei")
    rows[sym] = df
conn.close()

K_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5]

for sym, df in rows.items():
    label = sym.replace("BINANCE:", "")
    print(f"\n{'='*70}")
    print(f"{label}  DC Lower - k×ATR(14)  支撐位校準")
    print(f"{'='*70}")
    print(f"{'k值':<6} {'支撐均距':>8} {'均距%':>7} {'接近不破':>9} {'跌破':>7} {'守住(未到)':>11} {'樣本':>6}")
    print("-" * 60)

    snap = df[df["collected_at"].dt.hour == 16].copy().reset_index(drop=True)

    for k in K_VALUES:
        near_no_break = 0   # 接近（最低在支撐位上方 0~2%）且不跌破
        broke = 0           # 跌破
        held_away = 0       # 守住但最低價距支撐 >2%（沒被測試到）
        total = 0
        gaps = []

        for i, snap_row in snap.iterrows():
            start = snap_row["collected_at"]
            dc = snap_row["donchian_lower"]
            atr = snap_row["atr_14"]
            if pd.isna(dc) or pd.isna(atr):
                continue

            support = dc - k * atr
            gap_pct = (dc - support) / snap_row["price"] * 100
            gaps.append(dc - support)

            # 取接下來 24H 的資料
            end = start + pd.Timedelta(hours=24)
            window = df[(df["collected_at"] > start) & (df["collected_at"] <= end)]
            if window.empty:
                continue

            min_price = window["low"].min()
            cushion_pct = (min_price - support) / support * 100  # 正=在支撐上方

            total += 1
            if min_price < support:
                broke += 1
            elif cushion_pct <= 2.0:
                near_no_break += 1   # 接近（0~2%緩衝）且守住
            else:
                held_away += 1       # 守住但沒測試到

        if total == 0:
            continue
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        avg_gap_pct = avg_gap / snap["price"].mean() * 100
        print(
            f"k={k:<4}"
            f" {avg_gap:>8,.0f}"
            f" {avg_gap_pct:>6.2f}%"
            f" {near_no_break:>5}/{total} ({near_no_break/total*100:4.0f}%)"
            f" {broke:>3}/{total} ({broke/total*100:3.0f}%)"
            f" {held_away:>4}/{total} ({held_away/total*100:3.0f}%)"
            f" {total:>6}"
        )
