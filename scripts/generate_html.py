"""
generate_html.py
讀取 data/market_data.json + data/summary.json，
用 Jinja2 模板產生 index.html
"""

import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pct_class(val) -> str:
    """回傳漲跌 CSS class"""
    if val is None:
        return "neutral"
    return "up" if float(val) > 0 else ("down" if float(val) < 0 else "neutral")


def fmt_pct(val) -> str:
    if val is None:
        return "—"
    sign = "+" if float(val) > 0 else ""
    return f"{sign}{float(val):.2f}%"


def fmt_num(val) -> str:
    if val is None:
        return "—"
    return f"{float(val):,.2f}"


def fmt_vol(val) -> str:
    if val is None:
        return "—"
    v = int(val)
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return str(v)


def fmt_inst(val) -> str:
    """格式化法人買賣超（億元）"""
    if not val:
        return "—"
    v = int(val) / 100_000_000
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}億"


def main():
    market = load_json("data/market_data.json")
    summary = load_json("data/summary.json")

    generated_at = market.get("generated_at", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(generated_at)
        generated_str = dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        generated_str = generated_at

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["pct_class"] = pct_class
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_num"] = fmt_num
    env.filters["fmt_vol"] = fmt_vol
    env.filters["fmt_inst"] = fmt_inst

    tmpl = env.get_template("report.html.j2")
    html = tmpl.render(
        generated_str=generated_str,
        us=market.get("us", {}),
        tw=market.get("tw", {}),
        summary=summary,
    )

    os.makedirs("docs", exist_ok=True)
    out_path = "docs/index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"已產生 {out_path}")


if __name__ == "__main__":
    main()
