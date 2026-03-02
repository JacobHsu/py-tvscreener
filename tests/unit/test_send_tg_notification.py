import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from send_tg_notification import format_symbol_block

BASE = {
    "price": 67000.0,
    "change_pct": -0.01,
    "technical_rating": 0.1,
    "technical_rating_signal": "Buy",
    "ma_rating": 0.1,
    "ma_rating_signal": "Buy",
    "oscillators_rating": 0.0,
    "oscillators_rating_signal": "Neutral",
    "pivot_fib_s1": 65000.0,
    "pivot_fib_r1": 70000.0,
    "rsi_14": 50.0,
    "macd_level": 100.0,
    "macd_signal": 90.0,
    "macd_hist": 10.0,
    "adx_14": 25.0,
    "bb_lower": 65000.0,
    "donchian_lower": 64000.0,
    "atr_14": 800.0,
    "mfi": 50.0,
}

def make_data(**kwargs):
    d = dict(BASE)
    d.update(kwargs)
    return d

def test_vwap_vwma_same_direction_bold():
    """price > vwap 且 price > vwma → 兩者都粗體"""
    d = make_data(vwap=66000.0, vwma_20=65000.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "<b>66,000</b>" in msg or "<b>66,000.00</b>" in msg
    assert "<b>65,000</b>" in msg or "<b>65,000.00</b>" in msg

def test_vwap_vwma_opposite_direction_no_bold():
    """price > vwap 但 price < vwma → 兩者不粗體"""
    d = make_data(vwap=66000.0, vwma_20=68000.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP: $<b>" not in msg
    assert "VWMA: $<b>" not in msg

def test_vwap_vwma_both_bearish_bold():
    """price < vwap 且 price < vwma → 兩者都粗體"""
    d = make_data(price=64000.0, vwap=66000.0, vwma_20=65000.0)
    d["change_pct"] = -1.0
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP: $<b>" in msg
    assert "VWMA: $<b>" in msg

def test_vwap_none_no_bold():
    """vwap 為 None → 不加粗，不崩潰"""
    d = make_data(vwap=None, vwma_20=65000.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP" in msg
    assert "VWAP: $<b>" not in msg

def test_vwma_none_no_bold():
    """vwma_20 為 None → 不加粗"""
    d = make_data(vwap=66000.0, vwma_20=None)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP: $<b>" not in msg

def test_mfi_extreme_low_bold():
    """mfi < 20 → 粗體"""
    d = make_data(vwap=None, vwma_20=None, mfi=15.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "<b>15.0</b>" in msg or "<b>15</b>" in msg

def test_mfi_extreme_high_bold():
    """mfi > 80 → 粗體"""
    d = make_data(vwap=None, vwma_20=None, mfi=85.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "<b>85.0</b>" in msg or "<b>85</b>" in msg

def test_mfi_normal_no_bold():
    """mfi = 50 → 不粗體"""
    d = make_data(vwap=None, vwma_20=None, mfi=50.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "MFI: <b>" not in msg

def test_price_none_no_bold():
    """price 為 None → 不加粗"""
    d = make_data(price=None, vwap=66000.0, vwma_20=65000.0)
    d["change_pct"] = None
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP: $<b>" not in msg
    assert "VWMA: $<b>" not in msg


def test_adx_aroon_separate_line():
    """ADX 和 Aroon 在獨立行，RSI/MACD 在另一行"""
    d = make_data(adx_14=30.0, plus_di=25.0, minus_di=15.0, aroon_up=70.0, aroon_down=30.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "RSI:" in msg
    assert "MACD:" in msg
    assert "ADX:" in msg
    assert "Aroon:" in msg
    # RSI 和 ADX 不在同一行
    lines = msg.split("\n")
    rsi_line = next(l for l in lines if "RSI:" in l)
    adx_line = next(l for l in lines if "ADX:" in l)
    assert "ADX:" not in rsi_line
    assert "RSI:" not in adx_line

def test_adx_aroon_aligned_bullish_bold():
    """ADX ▲ 且 Aroon ▲ → 兩者粗體"""
    d = make_data(adx_14=30.0, plus_di=25.0, minus_di=15.0, aroon_up=80.0, aroon_down=20.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "ADX: <b>" in msg
    assert "Aroon: <b>" in msg

def test_adx_aroon_aligned_bearish_bold():
    """ADX ▼ 且 Aroon ▼ → 兩者粗體"""
    d = make_data(adx_14=30.0, plus_di=15.0, minus_di=25.0, aroon_up=20.0, aroon_down=80.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "ADX: <b>" in msg
    assert "Aroon: <b>" in msg

def test_adx_aroon_diverge_no_bold():
    """ADX ▲ 但 Aroon ▼ → 不粗體"""
    d = make_data(adx_14=30.0, plus_di=25.0, minus_di=15.0, aroon_up=20.0, aroon_down=80.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "ADX: <b>" not in msg
    assert "Aroon: <b>" not in msg

def test_adx_ranging_shows_equal():
    """ADX < 25 → (=)"""
    d = make_data(adx_14=18.0, plus_di=20.0, minus_di=15.0, aroon_up=40.0, aroon_down=60.0)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "(=)" in msg

def test_adx_aroon_none_no_crash():
    """Aroon 為 None → 不崩潰"""
    d = make_data(adx_14=30.0, plus_di=25.0, minus_di=15.0, aroon_up=None, aroon_down=None)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "ADX:" in msg
    assert "Aroon:" in msg
