"""
指標有效性回測：驗證各技術指標訊號出現後 24 小時的價格漲跌方向是否如預期。

方法：
    對每個訊號的 Bull（預期漲）/ Bear（預期跌）條件，篩出成立當下的樣本，
    計算未來 24 小時價格「真的照預期方向走」的比例（勝率），並與該幣種同期
    「無條件上漲機率」（baseline）比較，得出 edge（勝率 - baseline）。
    Edge 越高代表該訊號比純粹賭大盤慣性更有預測力。

除了單一指標，也測試幾組「組合訊號」（例如 Tech+RSI+EMA50 三重確認），
並與各分量單獨使用時的最佳 edge 比較，看組合是否真的比單獨看更準。

已知限制：24H 前瞻視窗為逐時滑動，相鄰樣本高度重疊（非獨立樣本），
與現有 analyze_dc_periods.py / calibrate_atr_support.py 的回測方式一致。

Usage:
    python scripts/backtest_indicator_accuracy.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"
REPORT_DIR = Path(__file__).parent.parent / "docs" / "indicator-backtest"
HORIZON = 24  # hours
MIN_N = 30    # 樣本數低於此值標註為參考

SYMBOLS = {
    "BTC": "BINANCE:BTCUSDT",
    "ETH": "BINANCE:ETHUSDT",
}


# ============================================================
# Data loading
# ============================================================
def load(symbol_db: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM technical_indicators WHERE symbol = ? ORDER BY collected_at",
        conn,
        params=(symbol_db,),
    )
    conn.close()
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True)
    df["fwd_return"] = df["price"].shift(-HORIZON) / df["price"] - 1
    return df


# ============================================================
# Single-indicator signal definitions: each returns (bull_mask, bear_mask)
# ============================================================
RATING_COLS = [
    ("Technical Rating", "technical_rating_signal"),
    ("MA Rating", "ma_rating_signal"),
    ("Oscillator Rating", "oscillators_rating_signal"),
]


def make_rating_signal(col):
    def f(df):
        bull = df[col].isin(["Buy", "Strong Buy"])
        bear = df[col].isin(["Sell", "Strong Sell"])
        return bull, bear
    return f


MA_COLS = [
    ("EMA10", "ema_10"), ("EMA20", "ema_20"), ("EMA50", "ema_50"),
    ("EMA100", "ema_100"), ("EMA200", "ema_200"),
    ("SMA10", "sma_10"), ("SMA20", "sma_20"), ("SMA50", "sma_50"),
    ("SMA100", "sma_100"), ("SMA200", "sma_200"),
    ("Hull MA9", "hull_ma_9"), ("VWMA20", "vwma_20"),
]


def make_ma_signal(col):
    def f(df):
        return df["price"] > df[col], df["price"] < df[col]
    return f


CANDLE_COLS = [
    ("K線-三白兵", "candle_3white_soldiers", "bull"),
    ("K線-三黑鴉", "candle_3black_crows", "bear"),
    ("K線-早晨之星", "candle_morning_star", "bull"),
    ("K線-黃昏之星", "candle_evening_star", "bear"),
    ("K線-多頭吞噬", "candle_engulfing_bull", "bull"),
    ("K線-空頭吞噬", "candle_engulfing_bear", "bear"),
    ("K線-錘形", "candle_hammer", "bull"),
    ("K線-倒錘形", "candle_inv_hammer", "bull"),
    ("K線-射擊之星", "candle_shooting_star", "bear"),
    ("K線-上吊線", "candle_hanging_man", "bear"),
]


def make_candle_signal(col, direction):
    def f(df):
        mask = df[col] == 1
        empty = pd.Series(False, index=df.index)
        return (mask, empty) if direction == "bull" else (empty, mask)
    return f


def sig_macd_hist(df):
    return df["macd_hist"] > 0, df["macd_hist"] < 0


def sig_macd_cross(df):
    return df["macd_level"] > df["macd_signal"], df["macd_level"] < df["macd_signal"]


def sig_rsi_extreme(df):
    """RSI(14) 逆勢反彈假設：< 30 預期反彈、> 70 預期回落。"""
    return df["rsi_14"] < 30, df["rsi_14"] > 70


def sig_rsi_trend(df):
    """RSI(14) 順勢假設（對照逆勢假設）：> 50 動能偏多、< 50 動能偏空。"""
    return df["rsi_14"] > 50, df["rsi_14"] < 50


def sig_stoch_k(df):
    return df["stoch_k"] < 20, df["stoch_k"] > 80


def sig_stoch_rsi_fast(df):
    return df["stoch_rsi_fast"] < 20, df["stoch_rsi_fast"] > 80


def sig_williams_r(df):
    return df["williams_r_14"] < -80, df["williams_r_14"] > -20


def sig_cci_sign(df):
    return df["cci_20"] > 0, df["cci_20"] < 0


def sig_cci_extreme(df):
    return df["cci_20"] < -100, df["cci_20"] > 100


def sig_awesome_osc(df):
    return df["awesome_osc"] > 0, df["awesome_osc"] < 0


def sig_momentum(df):
    return df["momentum_10"] > 0, df["momentum_10"] < 0


def sig_uo(df):
    return df["uo"] < 30, df["uo"] > 70


def sig_bbp(df):
    return df["bull_bear_power"] > 0, df["bull_bear_power"] < 0


def sig_adx_dir(df):
    trending = df["adx_14"] >= 25
    return (
        trending & (df["plus_di"] > df["minus_di"]),
        trending & (df["plus_di"] < df["minus_di"]),
    )


def sig_aroon(df):
    return df["aroon_up"] > df["aroon_down"], df["aroon_down"] > df["aroon_up"]


def sig_sar(df):
    return df["price"] > df["parabolic_sar"], df["price"] < df["parabolic_sar"]


def sig_trend_aligned(df):
    """ADX/Aroon/SAR 三向同向確認（通知粗體邏輯）。"""
    adx_bull = df["plus_di"] > df["minus_di"]
    adx_bear = df["plus_di"] < df["minus_di"]
    aroon_bull = df["aroon_up"] > df["aroon_down"]
    aroon_bear = df["aroon_down"] > df["aroon_up"]
    sar_bull = df["price"] > df["parabolic_sar"]
    sar_bear = df["price"] < df["parabolic_sar"]
    return (adx_bull & aroon_bull & sar_bull), (adx_bear & aroon_bear & sar_bear)


def sig_vwap_alone(df):
    return df["price"] > df["vwap"], df["price"] < df["vwap"]


def sig_vwma_alone(df):
    return df["price"] > df["vwma_20"], df["price"] < df["vwma_20"]


def sig_vwap_vwma(df):
    bull = (df["price"] > df["vwap"]) & (df["price"] > df["vwma_20"])
    bear = (df["price"] < df["vwap"]) & (df["price"] < df["vwma_20"])
    return bull, bear


def sig_cmf_alone(df):
    return df["cmf"] > 0, df["cmf"] < 0


def sig_mfi_trend(df):
    """MFI 順勢假設：> 50 偏多、< 50 偏空。"""
    return df["mfi"] > 50, df["mfi"] < 50


def sig_mfi_extreme(df):
    """MFI 逆勢假設：< 20 超賣預期反彈、> 80 超買預期回落。"""
    return df["mfi"] < 20, df["mfi"] > 80


def sig_cmf_mfi(df):
    bull = (df["cmf"] > 0) & (df["mfi"] > 50)
    bear = (df["cmf"] < 0) & (df["mfi"] < 50)
    return bull, bear


def sig_signal_emoji(df):
    """🟢/🔴 訊號（現行版）：RSI(14) 逆勢極端值 + ADX>20（send_tg_notification._signal_emoji）。"""
    trending = df["adx_14"] > 20
    return trending & (df["rsi_14"] < 30), trending & (df["rsi_14"] > 70)


def sig_signal_emoji_legacy(df):
    """🟢/🔴 訊號（舊版，已棄用）：ADX>20 前提下，KC突破+VWAP/VWMA+EMA200+RSI>50 四選三。

    保留於此僅供回測報告對照「改良前 vs 改良後」，正式通知已不使用此邏輯。
    """
    trending = df["adx_14"] > 20
    bull_count = (
        (df["price"] > df["keltner_upper"]).astype(int)
        + ((df["price"] > df["vwap"]) & (df["price"] > df["vwma_20"])).astype(int)
        + (df["price"] > df["ema_200"]).astype(int)
        + (df["rsi_14"] > 50).astype(int)
    )
    bear_count = (
        (df["price"] < df["keltner_lower"]).astype(int)
        + ((df["price"] < df["vwap"]) & (df["price"] < df["vwma_20"])).astype(int)
        + (df["price"] < df["ema_200"]).astype(int)
        + (df["rsi_14"] < 50).astype(int)
    )
    return trending & (bull_count >= 3), trending & (bear_count >= 3)


def sig_reversal(df):
    """空轉多/多轉空反轉訊號觸發條件（不分 monitor/complete 子狀態）。"""
    bull = (df["mfi"] < 20) & (df["rsi_14"] < 30)
    bear = (df["mfi"] > 80) & (df["rsi_14"] > 70)
    return bull, bear


SIGNAL_DEFS = (
    [(name, make_rating_signal(col)) for name, col in RATING_COLS]
    + [
        ("MACD Hist 方向 (▲/▼)", sig_macd_hist),
        ("MACD Level vs Signal 交叉", sig_macd_cross),
        ("RSI(14) 逆勢極端值", sig_rsi_extreme),
        ("RSI(14) 順勢(>50/<50)", sig_rsi_trend),
        ("Stochastic %K", sig_stoch_k),
        ("Stochastic RSI Fast", sig_stoch_rsi_fast),
        ("Williams %R", sig_williams_r),
        ("CCI(20) 順勢(正負號)", sig_cci_sign),
        ("CCI(20) 逆勢極端", sig_cci_extreme),
        ("Awesome Oscillator", sig_awesome_osc),
        ("Momentum(10)", sig_momentum),
        ("Ultimate Oscillator", sig_uo),
        ("Bull Bear Power", sig_bbp),
        ("ADX 方向 (+DI/-DI, ADX>=25)", sig_adx_dir),
        ("Aroon", sig_aroon),
        ("Parabolic SAR", sig_sar),
        ("ADX+Aroon+SAR 三向同向確認", sig_trend_aligned),
        ("VWAP(單獨)", sig_vwap_alone),
        ("VWMA(單獨)", sig_vwma_alone),
        ("VWAP/VWMA 同向", sig_vwap_vwma),
        ("CMF(單獨)", sig_cmf_alone),
        ("MFI 順勢(>50/<50)", sig_mfi_trend),
        ("MFI 逆勢極端(<20/>80)", sig_mfi_extreme),
        ("CMF/MFI 同向", sig_cmf_mfi),
        ("🟢/🔴 訊號(現行版)", sig_signal_emoji),
        ("🟢/🔴 訊號(舊版,已棄用)", sig_signal_emoji_legacy),
        ("空轉多/多轉空反轉訊號", sig_reversal),
    ]
    + [(name, make_candle_signal(col, direction)) for name, col, direction in CANDLE_COLS]
    + [(f"MA交叉-{name}", make_ma_signal(col)) for name, col in MA_COLS]
)


# ============================================================
# Combination signal definitions
# ============================================================
def combo_tech_rsi_ema50(df):
    """Tech 評級 + RSI 順勢(強弱) + 價格對 EMA50 位置，三重確認（趨勢延續假設）。

    靈感來自 scripts/README.md 的「最高風險組合」（Sell + RSI<35 + EMA50下方），
    但該原始組合是「進場風險警示」（避免在此時做多），不是「預測續跌」；
    這裡改用 24H 固定前瞻視窗測試「三個條件同向時，趨勢是否真的延續」，
    RSI 採順勢方向（>70 動能強勢/<30 動能疲弱），故對照分量用「RSI(14) 順勢」而非「逆勢極端值」。
    """
    bull = (
        df["technical_rating_signal"].isin(["Buy", "Strong Buy"])
        & (df["rsi_14"] > 70)
        & (df["price"] > df["ema_50"])
    )
    bear = (
        df["technical_rating_signal"].isin(["Sell", "Strong Sell"])
        & (df["rsi_14"] < 30)
        & (df["price"] < df["ema_50"])
    )
    return bull, bear


def combo_ma_osc_double(df):
    """MA Rating 與 Oscillator Rating 同方向雙重確認。"""
    bull = df["ma_rating_signal"].isin(["Buy", "Strong Buy"]) & df["oscillators_rating_signal"].isin(
        ["Buy", "Strong Buy"]
    )
    bear = df["ma_rating_signal"].isin(["Sell", "Strong Sell"]) & df["oscillators_rating_signal"].isin(
        ["Sell", "Strong Sell"]
    )
    return bull, bear


def combo_rsi_macd_agree(df):
    """RSI 逆勢極端 + MACD Hist 已同向翻轉（動能開始跟上）。"""
    bull = (df["rsi_14"] < 30) & (df["macd_hist"] > 0)
    bear = (df["rsi_14"] > 70) & (df["macd_hist"] < 0)
    return bull, bear


def combo_trend_triple_plus_tech(df):
    """ADX+Aroon+SAR 三向同向 再疊加 Tech 評級同向。"""
    adx_bull = df["plus_di"] > df["minus_di"]
    adx_bear = df["plus_di"] < df["minus_di"]
    aroon_bull = df["aroon_up"] > df["aroon_down"]
    aroon_bear = df["aroon_down"] > df["aroon_up"]
    sar_bull = df["price"] > df["parabolic_sar"]
    sar_bear = df["price"] < df["parabolic_sar"]
    tech_bull = df["technical_rating_signal"].isin(["Buy", "Strong Buy"])
    tech_bear = df["technical_rating_signal"].isin(["Sell", "Strong Sell"])
    bull = adx_bull & aroon_bull & sar_bull & tech_bull
    bear = adx_bear & aroon_bear & sar_bear & tech_bear
    return bull, bear


def combo_signal_emoji_plus_macd(df):
    """🟢/🔴 訊號(現行版) 再要求 MACD Hist 同向確認。"""
    emoji_bull, emoji_bear = sig_signal_emoji(df)
    bull = emoji_bull & (df["macd_hist"] > 0)
    bear = emoji_bear & (df["macd_hist"] < 0)
    return bull, bear


def combo_reversal_confirmed(df):
    """反轉訊號「CMF 已確認」子狀態（對應通知的 ✅ 完成版）。"""
    bull = (df["mfi"] < 20) & (df["rsi_14"] < 30) & (df["cmf"] > 0)
    bear = (df["mfi"] > 80) & (df["rsi_14"] > 70) & (df["cmf"] < 0)
    return bull, bear


def combo_reversal_monitor_only(df):
    """反轉訊號「僅監控中，CMF 未確認」子狀態。"""
    bull = (df["mfi"] < 20) & (df["rsi_14"] < 30) & (df["cmf"] <= 0)
    bear = (df["mfi"] > 80) & (df["rsi_14"] > 70) & (df["cmf"] >= 0)
    return bull, bear


def combo_volume_money_quad(df):
    """VWAP+VWMA+CMF+MFI 四個量能/資金流指標全部同向。"""
    bull = (
        (df["price"] > df["vwap"])
        & (df["price"] > df["vwma_20"])
        & (df["cmf"] > 0)
        & (df["mfi"] > 50)
    )
    bear = (
        (df["price"] < df["vwap"])
        & (df["price"] < df["vwma_20"])
        & (df["cmf"] < 0)
        & (df["mfi"] < 50)
    )
    return bull, bear


# 每個組合對照的「單獨分量」訊號名稱，用來算 combo 是否真的比單獨看更準
COMBO_DEFS = [
    ("Tech+RSI(順勢)+EMA50 三重確認", combo_tech_rsi_ema50,
     ["Technical Rating", "RSI(14) 順勢(>50/<50)", "MA交叉-EMA50"]),
    ("MA+Oscillator 雙評級同向", combo_ma_osc_double,
     ["MA Rating", "Oscillator Rating"]),
    ("RSI 逆勢+MACD 動能同向", combo_rsi_macd_agree,
     ["RSI(14) 逆勢極端值", "MACD Hist 方向 (▲/▼)"]),
    ("趨勢三向同向+Tech評級", combo_trend_triple_plus_tech,
     ["ADX+Aroon+SAR 三向同向確認", "Technical Rating"]),
    ("🟢/🔴 訊號(現行版)+MACD確認", combo_signal_emoji_plus_macd,
     ["🟢/🔴 訊號(現行版)", "MACD Hist 方向 (▲/▼)"]),
    ("反轉訊號-CMF已確認", combo_reversal_confirmed,
     ["空轉多/多轉空反轉訊號"]),
    ("反轉訊號-僅監控中(CMF未確認)", combo_reversal_monitor_only,
     ["空轉多/多轉空反轉訊號"]),
    ("VWAP+VWMA+CMF+MFI 四指標全同向", combo_volume_money_quad,
     ["VWAP/VWMA 同向", "CMF/MFI 同向"]),
]


# ============================================================
# 訊號 → 對應的 TG 通知欄位/技術指標（方便對照通知訊息時知道要看哪裡）
# ============================================================
INDICATOR_MAP = {
    "Technical Rating": "Tech",
    "MA Rating": "MA",
    "Oscillator Rating": "Oscillator",
    "MACD Hist 方向 (▲/▼)": "MACD",
    "MACD Level vs Signal 交叉": "MACD",
    "RSI(14) 逆勢極端值": "RSI",
    "RSI(14) 順勢(>50/<50)": "RSI",
    "Stochastic %K": "Stochastic %K",
    "Stochastic RSI Fast": "Stochastic RSI Fast",
    "Williams %R": "Williams %R",
    "CCI(20) 順勢(正負號)": "CCI",
    "CCI(20) 逆勢極端": "CCI",
    "Awesome Oscillator": "Awesome Oscillator",
    "Momentum(10)": "Momentum",
    "Ultimate Oscillator": "Ultimate Oscillator",
    "Bull Bear Power": "Bull Bear Power",
    "ADX 方向 (+DI/-DI, ADX>=25)": "ADX",
    "Aroon": "Aroon",
    "Parabolic SAR": "SAR",
    "ADX+Aroon+SAR 三向同向確認": "ADX + Aroon + SAR",
    "VWAP(單獨)": "VWAP",
    "VWMA(單獨)": "VWMA",
    "VWAP/VWMA 同向": "VWAP + VWMA",
    "CMF(單獨)": "CMF",
    "MFI 順勢(>50/<50)": "MFI",
    "MFI 逆勢極端(<20/>80)": "MFI",
    "CMF/MFI 同向": "CMF + MFI",
    "🟢/🔴 訊號(現行版)": "RSI + ADX",
    "🟢/🔴 訊號(舊版,已棄用)": "ADX + Keltner + VWAP + VWMA + EMA200 + RSI",
    "空轉多/多轉空反轉訊號": "MFI + RSI（CMF 決定文字狀態）",
    # combos
    "Tech+RSI(順勢)+EMA50 三重確認": "Tech + RSI + EMA50",
    "MA+Oscillator 雙評級同向": "MA + Oscillator",
    "RSI 逆勢+MACD 動能同向": "RSI + MACD",
    "趨勢三向同向+Tech評級": "ADX + Aroon + SAR + Tech",
    "🟢/🔴 訊號(現行版)+MACD確認": "🟢/🔴訊號 + MACD",
    "反轉訊號-CMF已確認": "MFI + RSI + CMF",
    "反轉訊號-僅監控中(CMF未確認)": "MFI + RSI + CMF",
    "VWAP+VWMA+CMF+MFI 四指標全同向": "VWAP + VWMA + CMF + MFI",
}


def indicator_for(name: str) -> str:
    if name in INDICATOR_MAP:
        return INDICATOR_MAP[name]
    if name.startswith("K線-"):
        return "K線型態"
    if name.startswith("MA交叉-"):
        return name.replace("MA交叉-", "")
    return name


# ============================================================
# Evaluation
# ============================================================
def evaluate_signal(name, fn, df, baseline_up):
    bull_mask, bear_mask = fn(df)
    valid = df["fwd_return"].notna()
    rows = []
    for direction, mask, want_up in [("Bull", bull_mask, True), ("Bear", bear_mask, False)]:
        sub = df.loc[mask & valid, "fwd_return"]
        n = len(sub)
        if n == 0:
            continue
        win_rate = (sub > 0).mean() if want_up else (sub < 0).mean()
        baseline = baseline_up if want_up else (1 - baseline_up)
        rows.append(
            {
                "技術指標": indicator_for(name),
                "判讀邏輯": name,
                "方向": direction,
                "N": n,
                "勝率%": win_rate * 100,
                "Baseline%": baseline * 100,
                "Edge(pp)": (win_rate - baseline) * 100,
                "平均24H報酬%": sub.mean() * 100,
                "備註": "⚠ N過小" if n < MIN_N else "",
            }
        )
    return rows


def evaluate_combo(name, fn, components, df, baseline_up, edge_lookup):
    rows = evaluate_signal(name, fn, df, baseline_up)
    for row in rows:
        direction = row["方向"]
        component_edges = [
            edge_lookup[(c, direction)] for c in components if (c, direction) in edge_lookup
        ]
        row["最佳單一分量Edge(pp)"] = max(component_edges) if component_edges else float("nan")
        row["組合增益(pp)"] = (
            row["Edge(pp)"] - row["最佳單一分量Edge(pp)"] if component_edges else float("nan")
        )
    return rows


# ============================================================
# Reliability tiering
# ============================================================
def tier_for(edge, n):
    if n < MIN_N:
        return "樣本過小(參考)"
    if edge >= 5:
        return "高可靠"
    if edge >= 1.5:
        return "中等"
    if edge > -1.5:
        return "接近雜訊"
    return "負向(不建議用於此方向)"


def run_for_symbol(label, symbol_db):
    df = load(symbol_db)
    baseline_up = (df["fwd_return"].dropna() > 0).mean()

    single_rows = []
    for name, fn in SIGNAL_DEFS:
        single_rows.extend(evaluate_signal(name, fn, df, baseline_up))
    single_result = pd.DataFrame(single_rows).sort_values("Edge(pp)", ascending=False)
    single_result["分級"] = single_result.apply(lambda r: tier_for(r["Edge(pp)"], r["N"]), axis=1)

    edge_lookup = {(r["判讀邏輯"], r["方向"]): r["Edge(pp)"] for r in single_rows}

    combo_rows = []
    for name, fn, components in COMBO_DEFS:
        combo_rows.extend(evaluate_combo(name, fn, components, df, baseline_up, edge_lookup))
    combo_result = pd.DataFrame(combo_rows).sort_values("Edge(pp)", ascending=False)

    n_valid = int(df["fwd_return"].notna().sum())

    print(f"\n{'=' * 90}")
    print(f"{label}  指標有效性回測（{HORIZON}H 前瞻，樣本 {n_valid} 筆，"
          f"Baseline 上漲率 {baseline_up * 100:.1f}%）")
    print(f"{'=' * 90}")
    with pd.option_context("display.max_rows", None, "display.width", 130):
        print(
            single_result.to_string(
                index=False,
                formatters={
                    "勝率%": "{:.1f}".format,
                    "Baseline%": "{:.1f}".format,
                    "Edge(pp)": "{:+.1f}".format,
                    "平均24H報酬%": "{:+.2f}".format,
                },
            )
        )
        print(f"\n--- {label} 組合訊號 ---")
        print(
            combo_result.to_string(
                index=False,
                formatters={
                    "勝率%": "{:.1f}".format,
                    "Baseline%": "{:.1f}".format,
                    "Edge(pp)": "{:+.1f}".format,
                    "平均24H報酬%": "{:+.2f}".format,
                    "最佳單一分量Edge(pp)": "{:+.1f}".format,
                    "組合增益(pp)": "{:+.1f}".format,
                },
            )
        )

    return {
        "label": label,
        "baseline_up": baseline_up,
        "n_valid": n_valid,
        "single": single_result,
        "combo": combo_result,
        "df": df,
    }


# ============================================================
# 通用版：BTC+ETH 樣本直接合併（pooled），排除雜訊/樣本過小後的總表
# ============================================================
NOISE_TIERS = {"接近雜訊", "樣本過小(參考)"}


def build_universal(results):
    combined_df = pd.concat([r["df"] for r in results], ignore_index=True)
    baseline_up = (combined_df["fwd_return"].dropna() > 0).mean()

    rows = []
    for name, fn in SIGNAL_DEFS:
        rows.extend(evaluate_signal(name, fn, combined_df, baseline_up))
    full = pd.DataFrame(rows).sort_values("Edge(pp)", ascending=False)
    full["分級"] = full.apply(lambda r: tier_for(r["Edge(pp)"], r["N"]), axis=1)

    display = full[~full["分級"].isin(NOISE_TIERS)].copy()

    return {
        "baseline_up": baseline_up,
        "n_valid": int(combined_df["fwd_return"].notna().sum()),
        "full": full,
        "display": display,
        "n_excluded": len(full) - len(display),
    }


# ============================================================
# Markdown report generation
# ============================================================
def _fmt_table(df, float_cols_1f=(), float_cols_pp=()):
    df = df.copy()
    for c in float_cols_1f:
        if c in df.columns:
            df[c] = df[c].map(lambda v: f"{v:.1f}")
    for c in float_cols_pp:
        if c in df.columns:
            df[c] = df[c].map(lambda v: f"{v:+.1f}" if pd.notna(v) else "—")
    return df.to_markdown(index=False)


def build_report(results, universal):
    lines = []
    lines.append("# 技術指標有效性回測報告\n")
    lines.append(
        "> 自動產生自 [`scripts/backtest_indicator_accuracy.py`](../../scripts/backtest_indicator_accuracy.py)，"
        "重新執行該腳本會覆寫本檔案。資料來源 `data/history.db`，資料範圍與抓取邏輯見 "
        "[復盤機制](../review-mechanism.md)。\n"
    )

    lines.append("## 1. 方法論\n")
    lines.append(
        f"- 對每個訊號定義 Bull（預期漲）/ Bear（預期跌）條件，篩出成立當下的樣本，"
        f"計算未來 **{HORIZON} 小時**價格是否真的照預期方向走（勝率）。\n"
        f"- **Baseline** = 該幣種同期「無條件上漲機率」（Bear 方向用 `1 - baseline`），"
        f"代表什麼指標都不看、純粹賭大盤慣性的準確度。\n"
        f"- **Edge** = 勝率 − Baseline，是本報告排名與判讀順序的核心依據。Edge 越高，"
        f"代表這個指標比單純跟隨當時大盤慣性多帶來的預測力越大。\n"
        f"- 樣本數 N < {MIN_N} 的訊號標註「⚠ N過小」，僅供參考，不計入可靠度分級。\n"
        f"- **已知限制**：{HORIZON}H 前瞻視窗逐時滑動，相鄰樣本高度重疊（非獨立樣本），"
        f"與專案既有回測腳本（`analyze_dc_periods.py`、`calibrate_atr_support.py`）手法一致，"
        f"沒有額外做自相關校正。此外本次資料涵蓋期間大盤偏多頭（BTC/ETH baseline 均 >50%），"
        f"若進入長期空頭或劇烈盤整，各指標的 edge 可能不同，建議未來資料累積更長後重跑本腳本更新結論。\n"
    )

    lines.append("## 2. 通用版（BTC+ETH 合併）— 逐一指標成效總表\n")
    lines.append(
        f"把 BTC、ETH 的樣本直接合併（pooled，共 {universal['n_valid']} 筆）重新計算一次，"
        f"代表「不分幣種、通用情況下」的結果，同期合併 Baseline **{universal['baseline_up']*100:.1f}%**。"
        f"已剔除「接近雜訊」與「樣本過小」共 {universal['n_excluded']} 個項目不列出——"
        f"這兩類數字本身就代表沒有可靠訊息，看了也沒用。個別幣種可能與此不同（見下方 3.1/3.2），"
        f"通用版適合用來判斷「這個指標值不值得長期放在通知裡」，個別幣種版適合判斷「現在這個幣要不要相信這個訊號」。\n"
    )
    lines.append(
        _fmt_table(
            universal["display"][
                ["技術指標", "判讀邏輯", "方向", "N", "勝率%", "Baseline%", "Edge(pp)", "平均24H報酬%", "分級", "備註"]
            ],
            float_cols_1f=["勝率%", "Baseline%"],
            float_cols_pp=["Edge(pp)", "平均24H報酬%"],
        )
    )
    lines.append("")

    lines.append("## 3. 各幣種逐一指標成效總表\n")
    for r in results:
        label = r["label"]
        lines.append(f"### 3.{'1' if label == 'BTC' else '2'} {label}\n")
        lines.append(
            f"樣本數 {r['n_valid']} 筆，同期無條件上漲機率（Baseline）**{r['baseline_up']*100:.1f}%**。\n"
        )
        table = r["single"][
            ["技術指標", "判讀邏輯", "方向", "N", "勝率%", "Baseline%", "Edge(pp)", "平均24H報酬%", "分級", "備註"]
        ]
        lines.append(
            _fmt_table(
                table,
                float_cols_1f=["勝率%", "Baseline%"],
                float_cols_pp=["Edge(pp)", "平均24H報酬%"],
            )
        )
        lines.append("")

    lines.append("## 4. 可靠度分級與判讀順序建議\n")
    lines.append(
        "| 分級 | 定義 | 建議用法 |\n|---|---|---|\n"
        "| 高可靠 | Edge ≥ +5pp 且 N ≥ 30 | 最先看，最值得當作方向依據 |\n"
        "| 中等 | Edge +1.5 ~ +5pp | 可輔助判斷，不建議單獨依賴 |\n"
        "| 接近雜訊 | Edge -1.5 ~ +1.5pp | 幾乎等於瞎猜，不建議作為判斷依據 |\n"
        "| 負向 | Edge < -1.5pp | 該方向的歷史表現比瞎猜還差，該指標出現時應保持警覺甚至反向解讀 |\n"
        "| 樣本過小(參考) | N < {} | 數字好看也不能信，資料不夠多 |\n".format(MIN_N)
    )

    for r in results:
        label = r["label"]
        high = r["single"][(r["single"]["分級"] == "高可靠")]
        neg = r["single"][(r["single"]["分級"] == "負向(不建議用於此方向)")]
        lines.append(f"### {label} 判讀順序建議\n")
        if not high.empty:
            order = ", ".join(
                f"{row['技術指標']}［{row['判讀邏輯']}］({row['方向']})"
                for _, row in high.sort_values("Edge(pp)", ascending=False).iterrows()
            )
            lines.append(f"**先看（高可靠，依 Edge 高到低）**：{order}\n")
        else:
            lines.append("**先看（高可靠）**：本次回測沒有指標達到高可靠門檻，需搭配組合訊號使用。\n")
        if not neg.empty:
            worst = neg.sort_values("Edge(pp)").head(10)
            warn = ", ".join(
                f"{row['技術指標']}［{row['判讀邏輯']}］({row['方向']})" for _, row in worst.iterrows()
            )
            suffix = f"（僅列最差 10 個，完整 {len(neg)} 個負向項目見上方總表）" if len(neg) > 10 else ""
            lines.append(f"**要小心（負向，出現時建議保持懷疑）**：{warn} {suffix}\n")
        lines.append("")

    lines.append("## 5. 組合訊號測試（誰要跟誰搭配一起看）\n")
    lines.append(
        "「組合增益(pp)」= 組合的 Edge − 組成分量中單獨表現最好的那個 Edge。"
        "正值代表「疊加確認真的更準」，負值代表「疊加反而稀釋了效果，不如只看最強的那個分量」。\n"
    )
    for r in results:
        label = r["label"]
        lines.append(f"### {label} 組合訊號\n")
        table = r["combo"][
            ["技術指標", "判讀邏輯", "方向", "N", "勝率%", "Baseline%", "Edge(pp)", "平均24H報酬%",
             "最佳單一分量Edge(pp)", "組合增益(pp)", "備註"]
        ]
        lines.append(
            _fmt_table(
                table,
                float_cols_1f=["勝率%", "Baseline%"],
                float_cols_pp=["Edge(pp)", "平均24H報酬%", "最佳單一分量Edge(pp)", "組合增益(pp)"],
            )
        )
        lines.append("")

    lines.append("## 6. 無法回測的部分\n")
    lines.append(
        "- **🗣️ 1H AI 預測**（GitHub Models GPT-4.1）：目前每次通知即時呼叫、不落地存檔，"
        "資料庫沒有歷史 AI 預測紀錄可回測。若要驗證其準確度，需先在 `send_tg_notification.py` "
        "把每次的 AI 預測結果連同時間戳寫回 DB，累積一段時間後才能回測。\n"
        "- **Fibonacci S1 多單進場策略、DC(S) 支撐位緩衝倍數**：已有正式回測結論"
        "（見 [交易策略說明](../trading-strategies.md)、[復盤機制](../review-mechanism.md)），"
        "計算方式是「進場後多久碰到停損/停利」的事件型回測，跟本報告固定 24H 前瞻視窗的方法論不同，"
        "本次不重複驗證，直接沿用既有結論。\n"
        "- **BB/KC Squeeze**：預測的是「波動壓縮即將突破」而非漲跌方向，不適合放進本報告的方向性排名，"
        "如需驗證可另外用「Squeeze 後平均絕對報酬是否比平常大」的方式測試（未來可擴充）。\n"
    )

    lines.append("## 7. 結論\n")
    lines.append(
        "1. 先看 [第 2 節通用版](#2-通用版btceth-合併-逐一指標成效總表) 挑出跨幣種都值得信任的指標；"
        "再對照 [第 3 節](#3-各幣種逐一指標成效總表) 確認個別幣種是否一致，把「高可靠」清單放在通知裡優先看。\n"
        "2. 沒有進到「高可靠」的單一指標，可以查[第 5 節](#5-組合訊號測試誰要跟誰搭配一起看)看有沒有搭配後組合增益轉正——"
        "如果組合增益是負的，代表疊加沒有意義，不如只看最強的那個分量就好。\n"
        "3. 「負向」分級的指標出現時要提高警覺：不是說它一定反著跑，而是歷史上這個方向的判斷還不如瞎猜，"
        "不該單獨依賴它做決策。\n"
        "4. 本報告基於 2026-02 至今、大盤總體偏多頭的資料區間，是否能推廣到空頭/劇烈震盪環境未知，"
        "建議之後資料更多時（尤其涵蓋過一次明顯回檔或空頭）重跑本腳本更新結論。\n"
    )

    return "\n".join(lines)


def write_report(results, universal):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "README.md"
    report_path.write_text(build_report(results, universal), encoding="utf-8")
    print(f"\n報告已輸出：{report_path}")


def main():
    results = []
    for label, symbol_db in SYMBOLS.items():
        results.append(run_for_symbol(label, symbol_db))

    universal = build_universal(results)
    print(f"\n{'=' * 90}")
    print(f"通用版（BTC+ETH 合併），樣本 {universal['n_valid']} 筆，"
          f"Baseline 上漲率 {universal['baseline_up'] * 100:.1f}%，"
          f"已剔除接近雜訊/樣本過小共 {universal['n_excluded']} 項")
    print(f"{'=' * 90}")
    with pd.option_context("display.max_rows", None, "display.width", 130):
        print(
            universal["display"].to_string(
                index=False,
                formatters={
                    "勝率%": "{:.1f}".format,
                    "Baseline%": "{:.1f}".format,
                    "Edge(pp)": "{:+.1f}".format,
                    "平均24H報酬%": "{:+.2f}".format,
                },
            )
        )

    write_report(results, universal)


if __name__ == "__main__":
    main()
