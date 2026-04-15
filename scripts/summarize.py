"""
summarize.py
讀取 data/market_data.json + data/analysis.json，
呼叫 Claude API 生成台股、美股繁中摘要，
輸出 data/summary.json
"""

import json
import os
import anthropic

MARKET_PATH = "data/market_data.json"
ANALYSIS_PATH = "data/analysis.json"
OUTPUT_PATH = "data/summary.json"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_pct(val) -> str:
    if val is None:
        return "—"
    sign = "+" if float(val) > 0 else ""
    return f"{sign}{float(val):.2f}%"


def fmt_inst(val) -> str:
    if not val:
        return "—"
    v = int(val) / 100_000_000
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}億"


def build_us_prompt(market: dict, analysis: dict) -> str:
    indices = market["us"]["indices"]
    a_indices = analysis["us"]["indices"]
    ranking = market["us"].get("ranking", {})
    anomalies = analysis["us"].get("anomalies", [])

    lines = ["【美股盤後資料】"]

    for name, d in indices.items():
        if not d:
            continue
        mood = a_indices.get(name, {}).get("market_mood", "")
        vol_sig = a_indices.get(name, {}).get("volume_analysis", {}).get("signal", "")
        lines.append(
            f"- {name}：{d['close']:,.2f}　漲跌 {fmt_pct(d['change_pct'])}　量能：{vol_sig}　氛圍：{mood}"
        )

    if ranking.get("top3"):
        tops = "、".join(f"{s['ticker']}({fmt_pct(s['change_pct'])})" for s in ranking["top3"])
        bots = "、".join(f"{s['ticker']}({fmt_pct(s['change_pct'])})" for s in ranking["bottom3"])
        lines.append(f"- 強勢：{tops}")
        lines.append(f"- 弱勢：{bots}")

    if anomalies:
        for a in anomalies[:3]:
            lines.append(f"- 異常：{a['ticker']} {a['reason']}")

    prompt_data = "\n".join(lines)

    return f"""{prompt_data}

請根據以上資料，用繁體中文寫一段 150~200 字的美股盤後摘要。
要求：
1. 說明大盤整體氛圍與量能狀況
2. 點出強弱個股或板塊特色
3. 如有異常暴量個股，請特別提及
4. 語氣客觀，像財經記者風格，不要給投資建議
5. 直接輸出摘要段落，不要加標題或項目符號"""


def build_tw_prompt(market: dict, analysis: dict) -> str:
    indices = market["tw"]["indices"]
    a_indices = analysis["tw"]["indices"]
    ranking = market["tw"].get("ranking", {})
    inst = market["tw"].get("institutional", {})
    anomalies = analysis["tw"].get("anomalies", [])

    lines = ["【台股盤後資料】"]

    for name, d in indices.items():
        if not d:
            continue
        mood = a_indices.get(name, {}).get("market_mood", "")
        vol_sig = a_indices.get(name, {}).get("volume_analysis", {}).get("signal", "")
        lines.append(
            f"- {name}：{d['close']:,.2f}　漲跌 {fmt_pct(d['change_pct'])}　量能：{vol_sig}　氛圍：{mood}"
        )

    if inst:
        lines.append(
            f"- 三大法人：外資 {fmt_inst(inst.get('foreign_net'))}　"
            f"投信 {fmt_inst(inst.get('trust_net'))}　"
            f"自營 {fmt_inst(inst.get('dealer_net'))}　"
            f"合計 {fmt_inst(inst.get('total_net'))}"
        )

    if ranking.get("top3"):
        tops = "、".join(f"{s['ticker']}({fmt_pct(s['change_pct'])})" for s in ranking["top3"])
        bots = "、".join(f"{s['ticker']}({fmt_pct(s['change_pct'])})" for s in ranking["bottom3"])
        lines.append(f"- 強勢：{tops}")
        lines.append(f"- 弱勢：{bots}")

    if anomalies:
        for a in anomalies[:3]:
            lines.append(f"- 異常：{a['ticker']} {a['reason']}")

    prompt_data = "\n".join(lines)

    return f"""{prompt_data}

請根據以上資料，用繁體中文寫一段 150~200 字的台股盤後摘要。
要求：
1. 說明加權指數表現與今日量能狀況
2. 說明三大法人動向對後市的意義
3. 點出強弱個股或族群
4. 如有異常暴量個股，請特別提及
5. 語氣客觀，像財經記者風格，不要給投資建議
6. 直接輸出摘要段落，不要加標題或項目符號"""


def call_claude(prompt: str, label: str) -> str:
    print(f"  呼叫 Claude API：{label}...")
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  [ERROR] {label}: {e}")
        return f"（摘要產生失敗：{e}）"


def main():
    print("=== 開始生成 AI 摘要 ===")
    market = load_json(MARKET_PATH)
    analysis = load_json(ANALYSIS_PATH)

    us_prompt = build_us_prompt(market, analysis)
    tw_prompt = build_tw_prompt(market, analysis)

    us_summary = call_claude(us_prompt, "美股")
    tw_summary = call_claude(tw_prompt, "台股")

    summary = {
        "us": us_summary,
        "tw": tw_summary,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n完成！已寫入 {OUTPUT_PATH}")
    print("\n── 美股摘要預覽 ──")
    print(us_summary[:120], "...")
    print("\n── 台股摘要預覽 ──")
    print(tw_summary[:120], "...")


if __name__ == "__main__":
    main()
