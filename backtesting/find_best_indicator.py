import sqlite3
import pandas as pd
from datetime import timedelta

# Configuration
DB_PATH = r'c:\github\tg\py-tvscreener\data\history.db'
TIMEZONE_OFFSET = 8  # Hours
START_HOUR_TW = 16
SYMBOLS = ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT']

# Define patterns for columns that represent Price Levels (not oscillators)
PRICE_INDICATOR_PATTERNS = [
    'ema_', 'sma_', 'hull_ma', 'vwma',   # Moving Averages
    'bb_', 'keltner_', 'donchian_',      # Bands/Channels
    'ichimoku_',                         # Ichimoku
    'pivot_',                            # Pivots
    'parabolic_sar', 'vwap'              # Overlays
]

def get_all_price_candidates(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(technical_indicators)")
    all_cols = [col[1] for col in cursor.fetchall()]
    
    candidates = []
    for col in all_cols:
        # Check if it matches any price indicator pattern
        if any(pat in col for pat in PRICE_INDICATOR_PATTERNS):
            candidates.append(col)
            
    return candidates

def run_analysis():
    conn = sqlite3.connect(DB_PATH)
    
    # Dynamically get candidates
    valid_candidates = get_all_price_candidates(conn)
    print(f"Scanning {len(valid_candidates)} potential price-based indicators...")
    
    cols_str = ", ".join(valid_candidates)
    query = f"""
    SELECT collected_at, symbol, price, low, {cols_str}
    FROM technical_indicators 
    WHERE symbol IN ('BINANCE:BTCUSDT', 'BINANCE:ETHUSDT')
    ORDER BY collected_at ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['collected_at'] = pd.to_datetime(df['collected_at'])
    df['tw_time'] = df['collected_at'] + timedelta(hours=TIMEZONE_OFFSET)

    results = []

    for symbol in SYMBOLS:
        symbol_df = df[df['symbol'] == symbol].sort_values('tw_time')
        # Filter for Session Start times
        session_points = symbol_df[symbol_df['tw_time'].dt.hour == START_HOUR_TW].copy()
        
        if session_points.empty:
            continue
            
        points = session_points.to_dict('records')
        
        for indicator in valid_candidates:
            total_sessions = 0
            pass_count = 0 
            total_dist_pct = 0.0 
            
            # Determine type
            is_pivot = 'pivot' in indicator
            
            for i in range(len(points) - 1):
                start_rec = points[i]
                start_time = start_rec['tw_time']
                
                # Validation: ensure next record is 24h later
                end_time = points[i+1]['tw_time']
                if (end_time - start_time) != timedelta(hours=24):
                    continue
                
                # Get session true low
                session_window = symbol_df[(symbol_df['tw_time'] >= start_time) & (symbol_df['tw_time'] < end_time)]
                if session_window.empty: continue
                
                true_low = session_window['low'].min()
                final_price = points[i+1]['price']
                
                support_val = start_rec[indicator]
                
                # Data cleanup check
                if support_val is None: continue
                # Simple heuristic: value must be somewhat close to price to be valid (e.g. within 50%)
                # This filters out indicators that might be on a different scale (though we filtered by name)
                if abs(support_val - final_price) > final_price * 0.5:
                    continue

                total_sessions += 1
                
                # Rule: PASS if Final Close >= Start Support
                if final_price >= support_val:
                    pass_count += 1
                
                # Distance: (True Low - Support) / True Low
                # Positive = Support is BELOW Low (Safe)
                # Negative = Support is ABOVE Low (Breached)
                dist = (true_low - support_val) / true_low
                total_dist_pct += dist
            
            if total_sessions > 0:
                win_rate = (pass_count / total_sessions) * 100
                avg_dist_to_low = (total_dist_pct / total_sessions) * 100
                
                results.append({
                    "Symbol": symbol,
                    "Indicator": indicator,
                    "Type": "Static" if is_pivot else "Dynamic",
                    "Win Rate": win_rate,
                    "Safe Distance %": avg_dist_to_low, # Renamed for clarity
                })

    res_df = pd.DataFrame(results)
    
    # Filter for 100% Win Rate
    # Sort by 'Safe Distance %' ascending (Closest to 0 is best, provided it's positive)
    # We want valid supports (positive distance usually), but strictly speaking
    # Win Rate only cares about Close. 
    # If we want "Safe Intraday", we want "Safe Distance" > 0.
    
    # Let's show top indicators
    res_df = res_df.sort_values(by=['Win Rate', 'Safe Distance %'], ascending=[False, True])
    
    print("\n" + "="*100)
    print("🏆 COMPREHENSIVE INDICATOR ANALYSIS")
    print("Sorted by: 1. Win Rate (High to Low) | 2. Safe Distance % (Low to High)")
    print("Note: Safe Dist % approx 0 means Support ~= Session Low (Perfect).")
    print("      Safe Dist % > 0 means Support < Session Low (Safe buffer).")
    print("      Safe Dist % < 0 means Support > Session Low (Intraday breach).")
    print("="*100)
    
    # Display top 40
    print(res_df.head(40).to_string(index=False, formatters={
        "Win Rate": lambda x: f"{x:.0f}%",
        "Safe Distance %": lambda x: f"{x:.2f}%"
    }))

if __name__ == "__main__":
    run_analysis()
