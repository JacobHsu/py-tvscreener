"""
Send TradingView 1H BTC/ETH technical notification to Telegram.

Reads the latest data from SQLite (written by collect_to_db.py),
calls GitHub Models API for AI prediction, formats an HTML message,
and sends it via the Telegram Bot API.

Usage:
    python scripts/send_tg_notification.py          # send to Telegram
    python scripts/send_tg_notification.py --dry-run # print only, don't send
"""

import logging
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ============================================================
# Constants
# ============================================================
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

TAIPEI_TZ = timezone(timedelta(hours=8))

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_MODEL = "openai/gpt-4.1"


# ============================================================
# Local .env loader (for development)
# ============================================================
def load_env():
    """Load .env file if it exists (local dev only)."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if key and value and not os.getenv(key):
                    os.environ[key] = value


# ============================================================
# Telegram
# ============================================================
def send_telegram_message(message: str) -> bool:
    """Send HTML message to Telegram via Bot API."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        log.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping send")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            log.info("Telegram message sent successfully")
            return True
        else:
            log.error("Telegram send failed: %d %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        log.error("Telegram send error: %s", e)
        return False


# ============================================================
# Database
# ============================================================
def get_latest_data() -> dict:
    """Return latest BTC & ETH rows from SQLite as {symbol: dict}."""
    if not DB_PATH.exists():
        log.error("Database not found: %s", DB_PATH)
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.execute(
        "SELECT DISTINCT collected_at FROM technical_indicators "
        "ORDER BY collected_at DESC LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return {}

    latest_time = row["collected_at"]
    log.info("Latest data timestamp: %s", latest_time)

    cur = conn.execute(
        "SELECT * FROM technical_indicators WHERE collected_at = ?",
        (latest_time,),
    )
    data = {}
    for r in cur.fetchall():
        data[r["symbol"]] = dict(r)
    conn.close()
    return data


# ============================================================
# Helpers
# ============================================================
def _safe(val):
    """Return None if value is None or NaN."""
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except TypeError:
        pass
    return val


def fmt_price(val):
    """Format price with commas. BTC-scale (>=100) no decimals, else 2."""
    val = _safe(val)
    if val is None:
        return "—"
    if abs(val) >= 100:
        return f"{val:,.0f}"
    return f"{val:,.2f}"


def fmt_num(val, decimals=1):
    """Format a number with fixed decimals."""
    val = _safe(val)
    if val is None:
        return "—"
    return f"{val:,.{decimals}f}"


def rating_signal(value) -> str:
    """Numeric rating (-1..+1) → human-readable signal."""
    val = _safe(value)
    if val is None:
        return "—"
    v = float(val)
    if v >= 0.5:
        return "Strong Buy"
    if v >= 0.1:
        return "Buy"
    if v > -0.1:
        return "Neutral"
    if v > -0.5:
        return "Sell"
    return "Strong Sell"


# ============================================================
# MA / Oscillator Buy-Sell Counts
# ============================================================
MA_KEYS = [
    "ema_10", "ema_20", "ema_50", "ema_100", "ema_200",
    "sma_10", "sma_20", "sma_50", "sma_100", "sma_200",
    "hull_ma_9", "vwma_20",
]


def compute_ma_counts(d: dict):
    """Count Buy/Sell among 12 Moving Averages (price vs MA)."""
    price = _safe(d.get("price"))
    if price is None:
        return 0, 0
    buy = sell = 0
    for k in MA_KEYS:
        v = _safe(d.get(k))
        if v is None:
            continue
        if price > v:
            buy += 1
        elif price < v:
            sell += 1
    return buy, sell


def compute_osc_counts(d: dict):
    """Count Buy/Sell among oscillators using TradingView-like rules."""
    buy = sell = 0

    # RSI(14): <30 Buy, >70 Sell
    rsi = _safe(d.get("rsi_14"))
    if rsi is not None:
        if rsi < 30:
            buy += 1
        elif rsi > 70:
            sell += 1

    # Stochastic %K: <20 Buy, >80 Sell
    stoch_k = _safe(d.get("stoch_k"))
    if stoch_k is not None:
        if stoch_k < 20:
            buy += 1
        elif stoch_k > 80:
            sell += 1

    # CCI(20): <-100 Buy, >100 Sell
    cci = _safe(d.get("cci_20"))
    if cci is not None:
        if cci < -100:
            buy += 1
        elif cci > 100:
            sell += 1

    # ADX: +DI > -DI → Buy, +DI < -DI → Sell
    plus_di = _safe(d.get("plus_di"))
    minus_di = _safe(d.get("minus_di"))
    if plus_di is not None and minus_di is not None:
        if plus_di > minus_di:
            buy += 1
        elif plus_di < minus_di:
            sell += 1

    # Awesome Oscillator: >0 Buy, <0 Sell
    ao = _safe(d.get("awesome_osc"))
    if ao is not None:
        if ao > 0:
            buy += 1
        elif ao < 0:
            sell += 1

    # Momentum(10): >0 Buy, <0 Sell
    mom = _safe(d.get("momentum_10"))
    if mom is not None:
        if mom > 0:
            buy += 1
        elif mom < 0:
            sell += 1

    # MACD: Level > Signal → Buy, Level < Signal → Sell
    macd_l = _safe(d.get("macd_level"))
    macd_s = _safe(d.get("macd_signal"))
    if macd_l is not None and macd_s is not None:
        if macd_l > macd_s:
            buy += 1
        elif macd_l < macd_s:
            sell += 1

    # Stoch RSI Fast: <20 Buy, >80 Sell
    srsi = _safe(d.get("stoch_rsi_fast"))
    if srsi is not None:
        if srsi < 20:
            buy += 1
        elif srsi > 80:
            sell += 1

    # Williams %R: <-80 Buy, >-20 Sell
    wr = _safe(d.get("williams_r_14"))
    if wr is not None:
        if wr < -80:
            buy += 1
        elif wr > -20:
            sell += 1

    # Bull Bear Power: >0 Buy, <0 Sell
    bbp = _safe(d.get("bull_bear_power"))
    if bbp is not None:
        if bbp > 0:
            buy += 1
        elif bbp < 0:
            sell += 1

    # Ultimate Oscillator: <30 Buy, >70 Sell
    uo = _safe(d.get("uo"))
    if uo is not None:
        if uo < 30:
            buy += 1
        elif uo > 70:
            sell += 1

    return buy, sell


# ============================================================
# AI Prediction (GitHub Models API)
# ============================================================
STYLE_GUIDE = """Movement style rules (choose exactly one):
- 單邊上漲: Strong uptrend, most indicators bullish, price breaking resistance
- 震盪偏多: Oscillating with bullish bias, mixed signals but leaning up
- 震盪偏空: Oscillating with bearish bias, mixed signals but leaning down
- 單邊下跌: Strong downtrend, most indicators bearish, price breaking support"""

REASON_GUIDELINES = """REASON guidelines (Traditional Chinese, max 50 chars):
- Must include specific indicator values (e.g. RSI 34, MACD -280, CCI -210)
- Must include key price levels (MA20, S1, R1, BB, DC)
- Must describe technical structure (跌破MA20, MACD死叉, 超賣反彈)
- Be concise and data-driven, no vague descriptions"""


def build_technical_summary(symbol: str, d: dict) -> str:
    """Build concise technical data summary for AI prompt."""
    lines = []

    lines.append(f"Price: ${fmt_price(d.get('price'))}")
    lines.append(f"Change: {_safe(d.get('change_pct')) or 0:+.2f}%")
    lines.append(f"High: ${fmt_price(d.get('high'))}")
    lines.append(f"Low: ${fmt_price(d.get('low'))}")

    lines.append("\nRatings (1H):")
    lines.append(f"  Technical: {d.get('technical_rating_signal', '—')}")
    lines.append(f"  MA: {d.get('ma_rating_signal', '—')}")
    lines.append(f"  Oscillators: {d.get('oscillators_rating_signal', '—')}")

    lines.append("\nOscillators:")
    lines.append(f"  RSI(14): {fmt_num(d.get('rsi_14'))}")
    lines.append(f"  Stochastic %K: {fmt_num(d.get('stoch_k'))}")
    lines.append(f"  Stochastic %D: {fmt_num(d.get('stoch_d'))}")
    lines.append(f"  MACD Level: {fmt_num(d.get('macd_level'))}")
    lines.append(f"  MACD Signal: {fmt_num(d.get('macd_signal'))}")
    lines.append(f"  MACD Hist: {fmt_num(d.get('macd_hist'))}")
    lines.append(f"  CCI(20): {fmt_num(d.get('cci_20'))}")
    lines.append(f"  ADX(14): {fmt_num(d.get('adx_14'))}")
    lines.append(f"  Stoch RSI Fast: {fmt_num(d.get('stoch_rsi_fast'))}")
    lines.append(f"  ROC(9): {fmt_num(d.get('roc_9'))}")
    lines.append(f"  Williams %R: {fmt_num(d.get('williams_r_14'))}")
    lines.append(f"  Momentum(10): {fmt_num(d.get('momentum_10'))}")

    lines.append("\nMoving Averages:")
    lines.append(f"  EMA20: {fmt_price(d.get('ema_20'))}")
    lines.append(f"  EMA50: {fmt_price(d.get('ema_50'))}")
    lines.append(f"  SMA20: {fmt_price(d.get('sma_20'))}")
    lines.append(f"  SMA50: {fmt_price(d.get('sma_50'))}")

    lines.append("\nBollinger Bands:")
    lines.append(f"  Upper: {fmt_price(d.get('bb_upper'))}")
    lines.append(f"  Lower: {fmt_price(d.get('bb_lower'))}")

    lines.append("\nDonchian Channels:")
    lines.append(f"  Upper: {fmt_price(d.get('donchian_upper'))}")
    lines.append(f"  Lower: {fmt_price(d.get('donchian_lower'))}")

    lines.append("\nPivot Fibonacci:")
    lines.append(f"  S1: {fmt_price(d.get('pivot_fib_s1'))}")
    lines.append(f"  R1: {fmt_price(d.get('pivot_fib_r1'))}")

    lines.append("\nVolatility & Volume:")
    lines.append(f"  ATR(14): {fmt_num(d.get('atr_14'))}")
    lines.append(f"  VWAP: {fmt_price(d.get('vwap'))}")
    lines.append(f"  MFI: {fmt_num(d.get('mfi'))}")

    return "\n".join(lines)


def predict_with_ai(symbol_short: str, d: dict) -> dict | None:
    """Call GitHub Models API (GPT-4.1) for 1H prediction."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        log.warning("GITHUB_TOKEN not set — skipping AI prediction")
        return None

    technical_summary = build_technical_summary(symbol_short, d)

    prompt = (
        f"You are a crypto technical analyst. Analyze the following {symbol_short} "
        f"technical indicators and predict the direction for the NEXT 1 HOUR.\n\n"
        f"Technical Data for {symbol_short}:\n{technical_summary}\n\n"
        f"{STYLE_GUIDE}\n\n"
        f"{REASON_GUIDELINES}\n\n"
        f"Respond in this exact format:\n"
        f"PREDICTION: [Up or Down]\n"
        f"STYLE: [走勢類型]\n"
        f"REASON: [具體技術理由]"
    )

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GITHUB_MODELS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional crypto technical analyst. Be concise and direct.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 200,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(
            GITHUB_MODELS_URL, headers=headers, json=payload, timeout=30
        )
        if resp.status_code != 200:
            log.error("GitHub Models API error: %d %s", resp.status_code, resp.text)
            return None

        content = resp.json()["choices"][0]["message"]["content"]
        log.info("AI response for %s: %s", symbol_short, content.strip())
        return parse_prediction(content)
    except Exception as e:
        log.error("AI prediction error for %s: %s", symbol_short, e)
        return None


def parse_prediction(content: str) -> dict | None:
    """Parse AI response into {prediction, style, reason}."""
    prediction = None
    style = None
    reason = None

    for line in content.strip().split("\n"):
        if line.startswith("PREDICTION:"):
            text = line.replace("PREDICTION:", "").strip()
            if "Up" in text or "up" in text:
                prediction = "Up"
            elif "Down" in text or "down" in text:
                prediction = "Down"
        elif line.startswith("STYLE:"):
            style = line.replace("STYLE:", "").strip()
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()

    if not prediction:
        return None

    valid_styles = ["單邊上漲", "震盪偏多", "震盪偏空", "單邊下跌"]
    if style not in valid_styles:
        style = "震盪偏多" if prediction == "Up" else "震盪偏空"

    return {"prediction": prediction, "style": style, "reason": reason or "—"}


# ============================================================
# Message Formatting
# ============================================================
def _macd_arrow(hist):
    """MACD histogram direction arrow."""
    hist = _safe(hist)
    if hist is None:
        return ""
    return "▲" if hist > 0 else "▼" if hist < 0 else "▬"


def format_symbol_block(d: dict, emoji: str, symbol_short: str, pred: dict | None) -> str:
    """Format one symbol's notification block (HTML)."""
    price = _safe(d.get("price"))
    change_pct = _safe(d.get("change_pct"))
    lines = []

    # ── Header: 【 🔶 BTC $67,564 -7 (-0.01%) 】
    price_str = fmt_price(price)
    if change_pct is not None and price is not None:
        abs_change = price * change_pct / 100
        change_str = f"{abs_change:+,.0f}" if abs(abs_change) >= 1 else f"{abs_change:+,.2f}"
        pct_str = f"{change_pct:+.2f}%"
    else:
        change_str = "—"
        pct_str = "—"

    lines.append(f"【 {emoji} <b>{symbol_short}</b> ${price_str} {change_str} ({pct_str}) 】")
    lines.append("")

    # ── Technical rating
    overall = d.get("technical_rating_signal") or rating_signal(d.get("technical_rating"))
    lines.append(f"⚠️ Tech: <b>{overall}</b>")

    # ── MA counts
    ma_buy, ma_sell = compute_ma_counts(d)
    ma_sig = d.get("ma_rating_signal") or rating_signal(d.get("ma_rating"))
    ma_line = f"MA: <b>{ma_sig}</b> Buy: (<b>{ma_buy}</b>) Sell: (<b>{ma_sell}</b>)"
    if ma_sell > ma_buy:
        ma_line += " ✘"
    lines.append(ma_line)

    # ── Oscillator counts
    osc_buy, osc_sell = compute_osc_counts(d)
    osc_sig = d.get("oscillators_rating_signal") or rating_signal(d.get("oscillators_rating"))
    lines.append(f"Oscillator: <b>{osc_sig}</b> Buy: (<b>{osc_buy}</b>) Sell: (<b>{osc_sell}</b>)")

    # ── Fibonacci pivots (bold the one closer to price)
    fib_s1 = _safe(d.get("pivot_fib_s1"))
    fib_r1 = _safe(d.get("pivot_fib_r1"))
    if fib_s1 is not None and fib_r1 is not None:
        s1_str = fmt_price(fib_s1)
        r1_str = fmt_price(fib_r1)
        if price is not None and abs(price - fib_s1) < abs(price - fib_r1):
            lines.append(f"Fibonacci: S1 <b>${s1_str}</b> | R1 ${r1_str}")
        else:
            lines.append(f"Fibonacci: S1 ${s1_str} | R1 <b>${r1_str}</b>")

    # ── RSI | MACD | ADX
    rsi = _safe(d.get("rsi_14"))
    macd_hist = _safe(d.get("macd_hist"))
    adx = _safe(d.get("adx_14"))

    rsi_str = fmt_num(rsi)
    rsi_extreme = rsi is not None and (rsi < 30 or rsi > 70)
    rsi_display = f"<b>{rsi_str}</b>" if rsi_extreme else rsi_str

    macd_str = f"{macd_hist:+.1f}" if macd_hist is not None else "—"
    macd_dir = _macd_arrow(macd_hist)

    adx_str = fmt_num(adx)
    adx_extreme = adx is not None and adx > 50
    adx_display = f"<b>{adx_str}</b>" if adx_extreme else adx_str
    adx_label = "(Trending)" if adx is not None and adx >= 25 else "(Ranging)"

    lines.append(f"RSI: {rsi_display} | MACD: {macd_str} {macd_dir} | ADX: {adx_display} {adx_label}")

    # ── BB | DC (bold) | ATR
    bb_lower = _safe(d.get("bb_lower"))
    dc_lower = _safe(d.get("donchian_lower"))
    atr = _safe(d.get("atr_14"))

    atr_pct = (atr / price * 100) if atr and price else None
    atr_volatile = atr_pct is not None and atr_pct >= 1.5
    atr_sym = "(~)" if atr_volatile else "(-)"
    atr_display = f"<b>{fmt_num(atr)}</b>" if atr_volatile else fmt_num(atr)

    lines.append(
        f"BB: ${fmt_price(bb_lower)} | DC: $<b>{fmt_price(dc_lower)}</b> | ATR: {atr_display} {atr_sym}"
    )

    # ── VWAP | MFI
    vwap = _safe(d.get("vwap"))
    mfi = _safe(d.get("mfi"))

    mfi_str = fmt_num(mfi)
    mfi_extreme = mfi is not None and (mfi < 20 or mfi > 80)
    mfi_display = f"<b>{mfi_str}</b>" if mfi_extreme else mfi_str

    lines.append(f"VWAP: ${fmt_price(vwap)} | MFI: {mfi_display}")

    # ── AI Prediction
    if pred:
        pred_emoji = "📈" if pred["prediction"] == "Up" else "📉"
        bull_bear = "🐂" if pred["prediction"] == "Up" else "🐻"
        lines.append(
            f'🗣️ 1H: {pred_emoji} <b>{pred["prediction"]} {pred["style"]}</b>'
        )
        lines.append(f'{bull_bear}: {pred["reason"]}')

    return "\n".join(lines)


def build_message(data: dict, predictions: dict) -> str:
    """Build the complete Telegram notification (HTML)."""
    now = datetime.now(TAIPEI_TZ)
    time_str = now.strftime("%Y-%m-%d %H:%M")

    parts = [f"🕐 {time_str} (台北時間)"]
    parts.append("")

    btc = data.get("BINANCE:BTCUSDT")
    if btc:
        parts.append(format_symbol_block(btc, "🔶", "BTC", predictions.get("BTC")))
        parts.append("")

    eth = data.get("BINANCE:ETHUSDT")
    if eth:
        parts.append(format_symbol_block(eth, "🔹", "ETH", predictions.get("ETH")))

    parts.append("")
    parts.append(
        "📊 <a href='https://tw.tradingview.com/crypto-coins-screener/'>TradingView Screener</a>"
    )

    return "\n".join(parts)


# ============================================================
# Main
# ============================================================
def main():
    load_env()

    dry_run = "--dry-run" in sys.argv

    data = get_latest_data()
    if not data:
        log.error("No data in database — nothing to send")
        sys.exit(1)

    # AI predictions (graceful failure — message still sends without them)
    predictions = {}
    for symbol, key in [("BTC", "BINANCE:BTCUSDT"), ("ETH", "BINANCE:ETHUSDT")]:
        d = data.get(key)
        if d:
            pred = predict_with_ai(symbol, d)
            if pred:
                predictions[symbol] = pred

    message = build_message(data, predictions)

    # Always print the message for logs
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print()
    print(message)
    print()

    if dry_run:
        log.info("Dry-run mode — message not sent")
        return

    ok = send_telegram_message(message)
    if not ok:
        log.error("Failed to send Telegram notification")
        sys.exit(1)


if __name__ == "__main__":
    main()
