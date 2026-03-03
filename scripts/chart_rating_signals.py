"""
Price + Rating Signal Chart
============================
上方：TradingView 1H K 線圖（互動式）
下方：price 走勢 + Technical / MA / Oscillator 評級色帶

用法：
    python scripts/chart_rating_signals.py              # BTC
    python scripts/chart_rating_signals.py ETHUSDT      # ETH

輸出：瀏覽器開啟 HTML 頁面
"""

import sys
import sqlite3
import tempfile
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── 設定 ──────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "history.db"

SIGNAL_COLOR = {
    "Strong Buy":  "#00c853",
    "Buy":         "#69f0ae",
    "Neutral":     "#90a4ae",
    "Sell":        "#ff5252",
    "Strong Sell": "#b71c1c",
}

SIGNAL_VALUE = {
    "Strong Buy":  2,
    "Buy":         1,
    "Neutral":     0,
    "Sell":        -1,
    "Strong Sell": -2,
}

# ── 主程式 ────────────────────────────────────────────
symbol_short = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
symbol = f"BINANCE:{symbol_short}"

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(
    """
    SELECT collected_at, open, high, low, price,
           donchian_lower,
           technical_rating_signal,
           ma_rating_signal,
           oscillators_rating_signal
    FROM technical_indicators
    WHERE symbol = ?
    ORDER BY collected_at
    """,
    conn,
    params=(symbol,),
)
conn.close()

if df.empty:
    print(f"No data for {symbol}")
    sys.exit(1)

# 轉換為 Asia/Taipei（UTC+8），與 TradingView 預設時區一致
df["collected_at"] = (
    pd.to_datetime(df["collected_at"], utc=True)
    .dt.tz_convert("Asia/Taipei")
)

# ── 每日 4pm 台北時間快照（階梯支撐線）──────────────────
def make_step_support(df, col, out_col):
    snap = (
        df[df["collected_at"].dt.hour == 16][["collected_at", col]]
        .copy()
        .rename(columns={col: out_col})
        .dropna(subset=[out_col])
    )
    return pd.merge_asof(df.sort_values("collected_at"), snap, on="collected_at")

df = make_step_support(df, "donchian_lower", "dc_support")
df["dc_support"] = df["dc_support"] * 0.98

# ── 圖表配置：1 price + 3 signal 子圖 ─────────────────
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    row_heights=[0.6, 0.13, 0.13, 0.13],
    vertical_spacing=0.02,
    subplot_titles=[
        f"{symbol_short} Price (1H)",
        "Technical Rating",
        "MA Rating",
        "Oscillator Rating",
    ],
)

# ── Row 1: Price line ─────────────────────────────────
fig.add_trace(
    go.Scatter(
        x=df["collected_at"],
        y=df["price"],
        mode="lines",
        name="Price",
        line=dict(color="#42a5f5", width=1.5),
    ),
    row=1, col=1,
)

fig.add_trace(
    go.Scatter(
        x=df["collected_at"],
        y=df["dc_support"],
        mode="lines",
        name="DC(S) -2% (4pm)",
        line=dict(color="#ff9800", width=1.5, shape="hv", dash="dot"),
        hovertemplate="DC(S): $%{y:,.0f}<br>%{x}<extra></extra>",
    ),
    row=1, col=1,
)


# Y 軸：右側，千位分隔符（對齊 TradingView）
fig.update_yaxes(
    tickformat=",.0f",
    tickprefix="$",
    side="right",
    row=1, col=1,
)

# ── Row 2-4: Signal color bars ────────────────────────
signal_cols = [
    ("technical_rating_signal",  2),
    ("ma_rating_signal",         3),
    ("oscillators_rating_signal", 4),
]

for col_name, row_num in signal_cols:
    for signal, color in SIGNAL_COLOR.items():
        mask = df[col_name] == signal
        if not mask.any():
            continue
        fig.add_trace(
            go.Bar(
                x=df.loc[mask, "collected_at"],
                y=[1] * mask.sum(),
                name=signal,
                marker_color=color,
                showlegend=(row_num == 2),  # legend 只在第一組顯示
                legendgroup=signal,
                hovertemplate=f"<b>{signal}</b><br>%{{x}}<extra></extra>",
            ),
            row=row_num, col=1,
        )
    fig.update_yaxes(
        showticklabels=False,
        range=[0, 1.2],
        row=row_num, col=1,
    )

# ── 佈局 ──────────────────────────────────────────────
fig.update_layout(
    title=f"{symbol_short} Price + Rating Signals",
    barmode="stack",
    height=700,
    template="plotly_dark",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    # x 軸時間格式：price 圖正下方顯示，格式對齊 TradingView
    xaxis=dict(
        showticklabels=True,
        tickformat="%b %d\n%H:%M",   # "Feb 10\n16:00"（TV 風格）
        tickangle=0,
        type="date",
    ),
    # 其他 signal x 軸隱藏標籤，避免重複
    xaxis2=dict(showticklabels=False),
    xaxis3=dict(showticklabels=False),
    xaxis4=dict(
        showticklabels=False,
        rangeslider=dict(visible=True, thickness=0.04),
        type="date",
    ),
)

# ── TradingView Widget HTML ───────────────────────────
tv_symbol = f"BINANCE:{symbol_short}"
tv_widget = f"""
<div style="background:#131722; padding:8px 0 0 0;">
  <div class="tradingview-widget-container" style="height:500px;">
    <div id="tradingview_chart"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "width": "100%",
      "height": 500,
      "symbol": "{tv_symbol}",
      "interval": "60",
      "timezone": "Asia/Taipei",
      "theme": "dark",
      "style": "1",
      "locale": "zh_TW",
      "toolbar_bg": "#131722",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "studies": ["STD;MA%Ribbon", "STD;Supertrend", "STD;VWMA"],
      "container_id": "tradingview_chart"
    }});
    </script>
  </div>
</div>
"""

# ── 組合 HTML：TradingView 上，Plotly 下 ─────────────
plotly_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{symbol_short} Rating Signals</title>
  <style>
    body {{ margin: 0; background: #131722; color: #d1d4dc; font-family: sans-serif; }}
    h2 {{ padding: 12px 16px 4px; margin: 0; font-size: 14px; color: #90a4ae; }}
  </style>
</head>
<body>
  <h2>TradingView 1H — {symbol_short}</h2>
  {tv_widget}
  <h2>Rating Signals — {symbol_short} ({len(df)} data points)</h2>
  {plotly_html}
</body>
</html>
"""

# ── 輸出到暫存 HTML 並開啟瀏覽器 ──────────────────────
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".html", delete=False, encoding="utf-8"
) as f:
    f.write(html)
    out_path = f.name

webbrowser.open(f"file://{out_path}")
print(f"Opened: {out_path}")
