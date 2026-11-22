import json
import os
from datetime import datetime, timezone, timedelta
import yfinance as yf

IST = timezone(timedelta(hours=5, minutes=30))
WATCHLIST_PATH = "watchlist.txt"
OUTPUT_PATH = "data/eod_prices.json"


def load_symbols(path):
    if not os.path.exists(path):
        return []
    syms = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip().upper().replace("-EQ", "")
            if s and not s.startswith("#"):
                syms.append(s)
    return sorted(set(syms))


def fetch_symbol(symbol):
    for suffix in (".NS", ".BO"):
        try:
            hist = yf.Ticker(f"{symbol}{suffix}").history(
                period="3mo", interval="1d", auto_adjust=False
            )
            if hist is None or hist.empty:
                continue
            hist = hist.dropna(subset=["Open", "High", "Low", "Close"])
            if hist.empty:
                continue

            candles = []
            for idx, row in hist.tail(65).iterrows():
                candles.append({
                    "time": int(idx.timestamp() * 1000),
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                })

            latest = candles[-1]
            prev = candles[-2]["close"] if len(candles) >= 2 else latest["open"]
            chg_pct = round(((latest["close"] - prev) / prev) * 100, 2) if prev else 0.0

            return {
                "symbol": symbol,
                "exchange": "NSE" if suffix == ".NS" else "BSE",
                "ltp": latest["close"],
                "prevClose": prev,
                "changePct": chg_pct,
                "asOf": latest["date"],
                "ohlc": candles,
            }
        except Exception as exc:
            print(f"[WARN] {symbol}{suffix}: {exc}")
    return None


def main():
    symbols = load_symbols(WATCHLIST_PATH)
    out = {
        "updatedAt": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "count": 0,
        "prices": {},
    }

    for sym in symbols:
        data = fetch_symbol(sym)
        if data:
            out["prices"][sym] = data
            print(f"[OK] {sym}: {data['ltp']} ({data['changePct']:+.2f}%)")
        else:
            print(f"[MISS] {sym}: no data")

    out["count"] = len(out["prices"])
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Saved {out['count']} symbols to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
