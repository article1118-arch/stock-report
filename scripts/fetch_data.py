"""
fetch_data.py
抓取台股與美股盤後資料，輸出 data/market_data.json
"""

import json
import os
from datetime import datetime, date
import yfinance as yf
import requests

OUTPUT_PATH = "data/market_data.json"

# ── 美股標的 ──────────────────────────────────────────────
US_INDICES = {
    "SPX": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow": "^DJI",
    "VIX": "^VIX",
}

US_STOCKS = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "GOOGL"]

# ── 台股標的 ──────────────────────────────────────────────
TW_INDICES = {
    "加權指數": "^TWII",
}

TW_STOCKS = [
    "2330.TW",  # 台積電
    "2317.TW",  # 鴻海
    "2454.TW",  # 聯發科
    "2308.TW",  # 台達電
    "2882.TW",  # 國泰金
]


def fetch_yf(ticker: str, period: str = "5d") -> dict | None:
    """用 yfinance 抓單一標的近期資料"""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period)
        if hist.empty:
            return None
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest
        change = latest["Close"] - prev["Close"]
        change_pct = change / prev["Close"] * 100
        vol_avg5 = hist["Volume"].mean()
        return {
            "close": round(float(latest["Close"]), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "volume": int(latest["Volume"]),
            "volume_avg5": int(vol_avg5),
            "volume_ratio": round(float(latest["Volume"]) / vol_avg5, 2) if vol_avg5 else None,
            "high": round(float(latest["High"]), 2),
            "low": round(float(latest["Low"]), 2),
            "history_5d": [
                {"date": str(idx.date()), "close": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
            ],
        }
    except Exception as e:
        print(f"  [WARN] {ticker}: {e}")
        return None


def fetch_tw_institutional() -> dict:
    """
    抓台股三大法人買賣超（TWSE 公開資料）
    來源：臺灣證券交易所 opendata API
    """
    try:
        today_str = date.today().strftime("%Y%m%d")
        url = (
            f"https://www.twse.com.tw/rwd/zh/fund/T86"
            f"?response=json&date={today_str}&selectType=ALL"
        )
        r = requests.get(url, timeout=10)
        d = r.json()
        if d.get("stat") != "OK":
            return {}
        # 最後一列為合計
        total_row = d["data"][-1]
        # 欄位順序：證券代號, 證券名稱, 外資買, 外資賣, 外資淨買, 投信買, 投信賣, 投信淨買, 自營買, 自營賣, 自營淨買, 三大法人合計
        def to_int(s):
            try:
                return int(str(s).replace(",", ""))
            except Exception:
                return 0
        return {
            "foreign_net": to_int(total_row[4]),
            "trust_net": to_int(total_row[7]),
            "dealer_net": to_int(total_row[10]),
            "total_net": to_int(total_row[11]),
        }
    except Exception as e:
        print(f"  [WARN] 三大法人: {e}")
        return {}


def rank_stocks(stocks_data: dict) -> dict:
    """依漲跌幅排出前3強、前3弱"""
    valid = {k: v for k, v in stocks_data.items() if v and v.get("change_pct") is not None}
    ranked = sorted(valid.items(), key=lambda x: x[1]["change_pct"], reverse=True)
    return {
        "top3": [{"ticker": k, **v} for k, v in ranked[:3]],
        "bottom3": [{"ticker": k, **v} for k, v in ranked[-3:]],
    }


def main():
    os.makedirs("data", exist_ok=True)
    print("=== 開始抓取市場資料 ===")

    # 美股指數
    print("美股指數...")
    us_indices = {}
    for name, ticker in US_INDICES.items():
        print(f"  {name} ({ticker})")
        us_indices[name] = fetch_yf(ticker)

    # 美股個股
    print("美股個股...")
    us_stocks = {}
    for ticker in US_STOCKS:
        print(f"  {ticker}")
        us_stocks[ticker] = fetch_yf(ticker)

    # 台股指數
    print("台股指數...")
    tw_indices = {}
    for name, ticker in TW_INDICES.items():
        print(f"  {name} ({ticker})")
        tw_indices[name] = fetch_yf(ticker)

    # 台股個股
    print("台股個股...")
    tw_stocks = {}
    for ticker in TW_STOCKS:
        print(f"  {ticker}")
        tw_stocks[ticker] = fetch_yf(ticker)

    # 三大法人
    print("台股三大法人...")
    institutional = fetch_tw_institutional()

    # 漲跌排名
    us_ranking = rank_stocks(us_stocks)
    tw_ranking = rank_stocks(tw_stocks)

    # 組合輸出
    output = {
        "generated_at": datetime.now().isoformat(),
        "us": {
            "indices": us_indices,
            "stocks": us_stocks,
            "ranking": us_ranking,
        },
        "tw": {
            "indices": tw_indices,
            "stocks": tw_stocks,
            "ranking": tw_ranking,
            "institutional": institutional,
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n完成！已寫入 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
