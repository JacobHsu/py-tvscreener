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
    "macd_macd": 100.0,
    "macd_signal": 90.0,
    "macd_hist": 10.0,
    "adx": 25.0,
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

def test_vwma_none_no_bold():
    """vwma_20 為 None → 不加粗"""
    d = make_data(vwap=66000.0, vwma_20=None)
    msg = format_symbol_block(d, "🔶", "BTC", None)
    assert "VWAP: $<b>" not in msg
