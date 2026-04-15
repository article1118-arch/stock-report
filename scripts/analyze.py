"""
analyze.py
讀取 data/market_data.json，計算技術指標與量能分析，
輸出 data/analysis.json
"""

import json
import os
import pandas as pd
import pandas_ta as ta

INPUT_PATH = "data/market_data.json"
OUTPUT_PATH = "data/analysis.json"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def history_to_df(history_5d: list) -> pd.DataFrame:
    """把 history_5d 列表轉成 DataFrame，index 為日期"""
    if not history_5d:
        return pd.DataFrame()
    df = pd.DataFrame(history_5d)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def volume_analysis(stock_data: dict) -> dict:
    """
    量能分析
    - volume_ratio: 今日量 / 5日均量（>1.5 視為爆量，<0.5 視為縮量）
    - signal: 文字判斷
    """
    vr = stock_data.get("volume_ratio")
    if vr is None:
        return {"volume_ratio": None, "signal": "資料不足"}
    if vr >= 2.0:
        signal = "巨量"
    elif vr >= 1.5:
        signal = "爆量"
    elif vr >= 1.2:
        signal = "量增"
    elif vr >= 0.8:
        signal = "量平"
    elif vr >= 0.5:
        signal = "縮量"
    else:
        signal = "極度縮量"
    return {"volume_ratio": vr, "signal": signal}


def tech_indicators(history_5d: list) -> dict:
    """
    用 pandas_ta 計算技術指標
    5日資料只能算短期均線；RSI/MACD 需要更長期資料，這裡做簡易版
    """
    df = history_to_df(history_5d)
    if df.empty or len(df) < 2:
        return {}

    result = {}

    # 5日高低點
    result["high_5d"] = round(float(df["close"].max()), 2)
    result["low_5d"] = round(float(df["close"].min()), 2)
    result["range_pct"] = round(
        (result["high_5d"] - result["low_5d"]) / result["low_5d"] * 100, 2
    )

    # 5日均線（MA5）
    ma5 = df["close"].mean()
    latest_close = df["close"].iloc[-1]
    result["ma5"] = round(float(ma5), 2)
    result["above_ma5"] = bool(latest_close > ma5)

    # 5日漲跌動能（最新 vs 最舊）
    oldest_close = df["close"].iloc[0]
    result["momentum_5d_pct"] = round(
        (latest_close - oldest_close) / oldest_close * 100, 2
    )

    return result


def classify_market(index_data: dict) -> str:
    """根據指數漲跌幅與量能給出市場氛圍"""
    pct = index_data.get("change_pct", 0) or 0
    vr = index_data.get("volume_ratio", 1) or 1

    if pct >= 1.5 and vr >= 1.3:
        return "強勢放量上攻"
    elif pct >= 0.5:
        return "溫和上漲"
    elif pct >= -0.5:
        return "盤整"
    elif pct >= -1.5:
        return "弱勢下跌"
    else:
        if vr >= 1.3:
            return "重挫放量"
        return "明顯下跌"


def analyze_stocks(stocks: dict) -> dict:
    """對每支個股做量能 + 技術分析"""
    result = {}
    for ticker, data in stocks.items():
        if not data:
            result[ticker] = None
            continue
        vol = volume_analysis(data)
        tech = tech_indicators(data.get("history_5d", []))
        result[ticker] = {
            "close": data.get("close"),
            "change_pct": data.get("change_pct"),
            "volume_analysis": vol,
            "tech": tech,
        }
    return result


def find_anomalies(stocks_analysis: dict) -> list:
    """找出異常個股：暴量 + 急漲/急跌"""
    anomalies = []
    for ticker, d in stocks_analysis.items():
        if not d:
            continue
        vr = d["volume_analysis"].get("volume_ratio") or 0
        pct = d.get("change_pct") or 0
        if vr >= 1.5 and abs(pct) >= 2:
            anomalies.append({
                "ticker": ticker,
                "change_pct": pct,
                "volume_ratio": vr,
                "reason": f"{'急漲' if pct > 0 else '急跌'}＋爆量（量比 {vr}x）",
            })
    anomalies.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return anomalies


def main():
    print("=== 開始分析 ===")
    market = load_json(INPUT_PATH)

    output = {}

    # 美股
    us_indices_analysis = {}
    for name, d in market["us"]["indices"].items():
        if d:
            us_indices_analysis[name] = {
                "market_mood": classify_market(d),
                "volume_analysis": volume_analysis(d),
            }

    us_stocks_analysis = analyze_stocks(market["us"]["stocks"])
    us_anomalies = find_anomalies(us_stocks_analysis)

    output["us"] = {
        "indices": us_indices_analysis,
        "stocks": us_stocks_analysis,
        "anomalies": us_anomalies,
    }

    # 台股
    tw_indices_analysis = {}
    for name, d in market["tw"]["indices"].items():
        if d:
            tw_indices_analysis[name] = {
                "market_mood": classify_market(d),
                "volume_analysis": volume_analysis(d),
            }

    tw_stocks_analysis = analyze_stocks(market["tw"]["stocks"])
    tw_anomalies = find_anomalies(tw_stocks_analysis)

    output["tw"] = {
        "indices": tw_indices_analysis,
        "stocks": tw_stocks_analysis,
        "anomalies": tw_anomalies,
        "institutional": market["tw"].get("institutional", {}),
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成！已寫入 {OUTPUT_PATH}")
    print(f"  美股異常個股：{len(us_anomalies)} 筆")
    print(f"  台股異常個股：{len(tw_anomalies)} 筆")


if __name__ == "__main__":
    main()
