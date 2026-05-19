"""
fetch_prices.py -- Luke 股市儀表板自動更新腳本
位置: fetch_prices.py (GitHub repo root)

排程:
  04:00  美股盤後結算 (台灣時間)
  08:30  台股開盤前
  13:30  台股收盤後
  21:00  美股開盤後 (台灣時間)

輸出: prices.js (dashboard 自動讀取)
"""

import json, os, sys
from datetime import datetime

def load_previous(out_file):
    try:
        with open(out_file, "r", encoding="utf-8") as f:
            raw = f.read()
        start = raw.index("window.LIVE_PRICES = ") + len("window.LIVE_PRICES = ")
        end   = raw.rindex("};") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"indices": {}, "stocks": {}}

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance -q")
    import yfinance as yf

INDICES = {
    "^TWII":     {"name": "台股加權",  "flag": "🇹🇼", "code": "TWII",   "region": "tw"},
    "^GSPC":     {"name": "S&P 500",  "flag": "🇺🇸", "code": "SPX",    "region": "us"},
    "^IXIC":     {"name": "NASDAQ",   "flag": "🇺🇸", "code": "IXIC",   "region": "us"},
    "^KS11":     {"name": "KOSPI",    "flag": "🇰🇷", "code": "KOSPI",  "region": "kr"},
    "^N225":     {"name": "日經225",  "flag": "🇯🇵", "code": "N225",   "region": "jp"},
    "^GDAXI":    {"name": "德國DAX",  "flag": "🇩🇪", "code": "DAX",    "region": "eu"},
    "000001.SS": {"name": "上證綜指", "flag": "🇨🇳", "code": "SSEC",   "region": "cn"},
    "^HSI":      {"name": "恆生指數", "flag": "🇭🇰", "code": "HSI",    "region": "hk"},
}

STOCKS = {
    "5289.TW": {"name": "宜鼎",  "code": "5289", "cost": 0,    "shares": 0,   "status": "watch"},
    "8064.TW": {"name": "東捷",  "code": "8064", "cost": 0,    "shares": 0,   "status": "watch"},
    "8027.TW": {"name": "鈦昇",  "code": "8027", "cost": 0,    "shares": 0,   "status": "watch"},
}

def fetch_ticker(symbol):
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        price   = round(float(fi.last_price), 2)
        prev    = round(float(fi.previous_close), 2)
        chg_abs = round(price - prev, 2)
        chg_pct = round((price / prev - 1) * 100, 2) if prev else 0
        return {"price": price, "prev": prev, "chg": chg_abs, "chg_pct": chg_pct, "ok": True}
    except Exception as e:
        return {"price": None, "prev": None, "chg": None, "chg_pct": None, "ok": False, "err": str(e)}

def fetch_ytd(symbol):
    try:
        t  = yf.Ticker(symbol)
        yr = datetime.now().year
        df = t.history(start=f"{yr}-01-01", period="ytd")
        if len(df) < 2:
            return None
        start_price = float(df["Close"].iloc[0])
        last_price  = float(df["Close"].iloc[-1])
        return round((last_price / start_price - 1) * 100, 1)
    except:
        return None

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 開始更新股價...")

    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.js")
    prev_data = load_previous(out_file)

    indices_out = {}
    for sym, meta in INDICES.items():
        code = meta["code"]
        r   = fetch_ticker(sym)
        ytd = fetch_ytd(sym)
        if r["ok"]:
            d = {**meta, **r, "ytd": ytd}
        else:
            prev = prev_data.get("indices", {}).get(code, {})
            if prev.get("ok") and prev.get("price"):
                d = {**prev, "fetch_note": f"cache ({prev_data.get('updated','')})", "ok": True}
            else:
                d = {**meta, **r, "ytd": ytd}
        indices_out[code] = d

    stocks_out = {}
    for sym, meta in STOCKS.items():
        code = meta["code"]
        r = fetch_ticker(sym)
        if r["ok"]:
            d = {**meta, "symbol": sym, **r}
            cost  = meta["cost"]
            pnl   = round((r["price"] - cost) * meta["shares"], 0) if cost and meta["shares"] else 0
            pnl_p = round((r["price"] / cost - 1) * 100, 1) if cost else 0
        else:
            prev = prev_data.get("stocks", {}).get(code, {})
            if prev.get("ok") and prev.get("price"):
                d = {**prev, "fetch_note": f"cache ({prev_data.get('updated','')})", "ok": True}
            else:
                d = {**meta, "symbol": sym, **r}
        stocks_out[code] = d

    js = f"""// auto-generated -- do not edit manually
// updated: {now}
window.LIVE_PRICES = {json.dumps({
    "indices": indices_out,
    "stocks":  stocks_out,
    "updated": now,
    "ok": True
}, ensure_ascii=False, indent=2)};
"""
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Done. Written to {out_file}")

if __name__ == "__main__":
    main()
