import sqlite3, pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/history.db")
df = pd.read_sql_query(
    "SELECT collected_at, price, low, donchian_lower "
    "FROM technical_indicators WHERE symbol='BINANCE:BTCUSDT' ORDER BY collected_at",
    conn,
)
conn.close()

df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True).dt.tz_convert("Asia/Taipei")
df = df.set_index("collected_at")

periods = [22, 24, 26, 28, 30, 35, 40, 48]
for n in periods:
    df[f"dc_{n}"] = df["low"].rolling(n).min()

snap = df[df.index.hour == 16].copy().dropna()

print(f"{'期間':<8} {'低於DC20':>8} {'平均差':>8} {'中位差':>8} {'std':>8} {'0~500差':>8} {'最大差':>8} {'最小差':>8}")
print("-" * 72)
for n in periods:
    col = f"dc_{n}"
    diff = snap["donchian_lower"] - snap[col]
    below = (diff > 0).mean() * 100
    in_range = diff.between(0, 500).mean() * 100
    print(
        f"DC({n:<2})  {below:>7.0f}%"
        f" {diff.mean():>+8,.0f}"
        f" {diff.median():>+8,.0f}"
        f" {diff.std():>8,.0f}"
        f" {in_range:>7.0f}%"
        f" {diff.max():>+8,.0f}"
        f" {diff.min():>+8,.0f}"
    )

print("\n=== 4pm 快照每日詳細值 ===")
cols = ["price", "donchian_lower"] + [f"dc_{n}" for n in periods]
print(snap[cols].round(0).to_string())
