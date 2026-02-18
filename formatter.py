#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Any
import json


MAX_LEN = 1000


INTENT_EMOJI = {
    "INDEX_REALTIME": "📈",
    "KLINE_ANALYSIS": "🕯️",
    "INTRADAY_ANALYSIS": "⏱️",
    "LIMIT_STATS": "🚦",
    "MONEY_FLOW": "💰",
    "FUNDAMENTAL": "📊",
    "MARGIN_LHB": "🏦",
    "SECTOR_ANALYSIS": "🧩",
    "DERIVATIVES": "📉",
    "FUND_BOND": "🏛️",
    "HK_US_MARKET": "🌍",
}


def _to_text(data: Any) -> str:
    if data is None:
        return "无数据"

    if isinstance(data, str):
        return data

    if isinstance(data, (dict, list, tuple)):
        import datetime as dt

        def convert(obj):
            if isinstance(obj, dt.date):
                return obj.isoformat()
            if isinstance(obj, (dict, list, tuple)):
                if isinstance(obj, dict):
                    return {k: convert(v) for k, v in obj.items()}
                return [convert(i) for i in obj]
            return obj

        data = convert(data)
        return json.dumps(data, ensure_ascii=False, indent=2)

    if hasattr(data, "to_dict"):
        try:
            as_dict = data.to_dict(orient="records")
            return json.dumps(as_dict, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return str(data)


def _truncate(text: str, limit: int = MAX_LEN) -> str:
    if len(text) <= limit:
        return text
    suffix = "\n...\n(内容过长，已截断)"
    keep = max(0, limit - len(suffix))
    return text[:keep] + suffix


def _safe_float(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
    try:
        return float(value)
    except Exception:
        return None


def _fmt_price(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return str(value) if value is not None else "?"
    return f"{num:.2f}"


def _fmt_pct(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "?"
    return f"{num:+.2f}%"


def _fmt_amount(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return str(value) if value is not None else "?"
    abs_num = abs(num)
    if abs_num >= 1e8:
        return f"{num / 1e8:.2f}亿"
    if abs_num >= 1e4:
        return f"{num / 1e4:.2f}万"
    return f"{num:.0f}"


def _fmt_date(value: Any) -> str:
    if value is None:
        return "未知"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _pick(item: dict, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in item and item.get(key) not in (None, ""):
            return item.get(key)
    return default


def _market_sentiment(changes: list[float]) -> str:
    if not changes:
        return "市场情绪：数据不足，偏中性。"

    pos = sum(1 for c in changes if c > 0)
    neg = sum(1 for c in changes if c < 0)
    avg_change = sum(changes) / len(changes)
    spread = max(changes) - min(changes)

    if avg_change >= 0.8 and pos >= 4:
        return "市场情绪：整体偏强，风险偏好回升。"
    if avg_change <= -0.8 and neg >= 4:
        return "市场情绪：整体偏弱，防御情绪升温。"
    if spread >= 1.0 and 2 <= pos <= 3:
        return "市场情绪：板块分化明显，结构性机会为主。"
    return "市场情绪：震荡整理，资金观望为主。"


def render_output(intent_obj, result, platform: str = "qq") -> str:
    _ = platform
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    emoji = INTENT_EMOJI.get(getattr(intent_obj, "intent", ""), "📌")
    intent = getattr(intent_obj, "intent", "")

    if intent == "INDEX_REALTIME" and result.get("ok"):
        items = result.get("data", {}).get("items", [])
        index_targets = [
            ("上证指数", ["上证指数", "上证综指", "沪指"]),
            ("深证成指", ["深证成指", "深证指数"]),
            ("创业板指", ["创业板指"]),
            ("沪深300", ["沪深300"]),
            ("上证50", ["上证50"]),
        ]

        selected = []
        for label, aliases in index_targets:
            matched = None
            for item in items:
                name = str(item.get("名称", ""))
                if any(alias in name for alias in aliases):
                    matched = item
                    break
            if matched:
                selected.append((label, matched))

        if not selected:
            selected = [(str(item.get("名称", "?")), item) for item in items[:5]]

        lines = [f"📊 A股实时大盘 · {ts}", ""]
        changes = []
        for label, item in selected:
            price = _pick(item, ["最新价", "最新点位", "收盘"])
            change = _pick(item, ["涨跌幅", "涨跌幅%", "涨跌"])
            amount = _pick(item, ["成交额", "成交金额", "成交额(元)", "总成交额"])

            change_num = _safe_float(change)
            if change_num is not None:
                changes.append(change_num)
            direction = "📈" if (change_num or 0) >= 0 else "📉"
            lines.append(
                f"{direction} {label}: {_fmt_price(price)} ({_fmt_pct(change)}) | 成交额 {_fmt_amount(amount)}"
            )

        lines.extend(["", f"💡 {_market_sentiment(changes)}", "", "数据源: akshare"])
        return _truncate("\n".join(lines), MAX_LEN)

    if intent == "KLINE_ANALYSIS":
        if not result.get("ok"):
            return "\n".join([f"{emoji} A股分析 · {ts}", f"\n⚠️ 错误: {result.get('error', '未知')}"])

        data = result.get("data", {})
        items = data.get("items", [])
        symbol = data.get("symbol") or getattr(intent_obj, "symbol", None) or ""
        stock_name = data.get("name") or data.get("名称")
        if not stock_name:
            query = getattr(intent_obj, "query", "")
            if query:
                try:
                    from router import STOCK_NAME_MAP

                    for name in sorted(STOCK_NAME_MAP, key=len, reverse=True):
                        if name in query:
                            stock_name = name
                            break
                except Exception:
                    stock_name = None
        if not stock_name:
            stock_name = symbol or "未知"

        display_name = f"{stock_name}({symbol})" if symbol else stock_name
        ts_date = datetime.now().strftime("%Y-%m-%d")
        count = getattr(intent_obj, "top_n", None) or len(items) or 0
        sections = [
            f"{emoji} {display_name} 近{count}日K线 · {ts_date}",
            "",
        ]

        show_items = items[:5]
        for item in show_items:
            if not isinstance(item, dict):
                sections.append(str(item))
                continue
            date_text = _fmt_date(_pick(item, ["日期", "date", "时间"]))
            open_price = _fmt_price(_pick(item, ["开盘", "open"]))
            close_price = _fmt_price(_pick(item, ["收盘", "close"]))
            change = _pick(item, ["涨跌幅", "pct_change", "涨跌幅%"])
            change_value = _safe_float(change)
            direction = "📈" if (change_value or 0) >= 0 else "📉"
            change_text = f" {direction} ({_fmt_pct(change)})" if change_value is not None else ""
            sections.append(f"📅 {date_text}: 开盘 {open_price} 收盘 {close_price}{change_text}")

        if len(items) > len(show_items):
            sections.append("...")

        sections.append("\n数据源: akshare")
        return _truncate("\n".join(sections), MAX_LEN)

    if intent == "INTRADAY_ANALYSIS":
        if not result.get("ok"):
            return "\n".join([f"{emoji} 分时分析 · {ts}", f"\n⚠️ 错误: {result.get('error', '未知')}"])

        data = result.get("data", {})
        items = data.get("items", [])
        symbol = data.get("symbol") or getattr(intent_obj, "symbol", "?") or "?"
        period = data.get("period") or getattr(intent_obj, "period", None) or "1"

        lines = [f"⏱️ {symbol} 分时({period}m) · {ts}", ""]
        if not items:
            lines.extend(["暂无分时数据", "", "数据源: akshare"])
            return "\n".join(lines)

        latest = items[0] if isinstance(items[0], dict) else {}
        latest_price = _pick(latest, ["收盘", "close", "最新价", "成交价", "价格"])
        high_price = _pick(latest, ["最高", "high"])
        low_price = _pick(latest, ["最低", "low"])
        volume = _pick(latest, ["成交量", "volume", "手数"])
        latest_time = _pick(latest, ["时间", "day", "datetime"])

        lines.append(
            f"最新 {_fmt_date(latest_time)} | 价 {_fmt_price(latest_price)} | 高 {_fmt_price(high_price)} | 低 {_fmt_price(low_price)} | 量 {_fmt_amount(volume)}"
        )
        lines.append("")
        lines.append("最近成交:")

        for item in items[:8]:
            if not isinstance(item, dict):
                lines.append(str(item))
                continue
            t = _fmt_date(_pick(item, ["时间", "day", "datetime"]))
            p = _fmt_price(_pick(item, ["收盘", "close", "成交价", "价格"]))
            v = _fmt_amount(_pick(item, ["成交量", "volume", "手数"]))
            direction = _pick(item, ["买卖盘性质", "性质"], "")
            tag = f" {direction}" if direction else ""
            lines.append(f"- {t}: {p} | 量 {v}{tag}")

        lines.extend(["", "数据源: akshare"])
        return _truncate("\n".join(lines), MAX_LEN)

    if intent == "LIMIT_STATS":
        if not result.get("ok"):
            return "\n".join([f"{emoji} 涨跌停统计 · {ts}", f"\n⚠️ 错误: {result.get('error', '未知')}"])

        data = result.get("data", {})
        date = _fmt_date(data.get("date") or getattr(intent_obj, "date", ""))
        up_items = data.get("up_items") or data.get("items") or []
        down_items = data.get("down_items") or []
        up_count = data.get("up_count")
        down_count = data.get("down_count")

        if up_count is None:
            up_count = len(up_items)
        if down_count is None:
            down_count = len(down_items)

        lines = [f"🚦 涨跌停统计 · {date}", "", f"涨停: {up_count} 家 | 跌停: {down_count} 家", "", "涨停前10:"]

        for idx, item in enumerate(up_items[:10], start=1):
            if not isinstance(item, dict):
                lines.append(f"{idx}. {item}")
                continue
            name = _pick(item, ["名称", "股票简称", "简称"], "?")
            code = _pick(item, ["代码", "股票代码", "symbol"], "?")
            pct = _pick(item, ["涨跌幅", "涨跌幅%"], None)
            board = _pick(item, ["连板数", "连板", "几天几板"], None)
            board_text = f" | 连板 {board}" if board not in (None, "") else ""
            pct_text = f" | {_fmt_pct(pct)}" if pct is not None else ""
            lines.append(f"{idx}. {name}({code}){pct_text}{board_text}")

        lines.extend(["", "数据源: akshare"])
        return _truncate("\n".join(lines), MAX_LEN)

    if intent == "MONEY_FLOW":
        if not result.get("ok"):
            return "\n".join([f"{emoji} 资金流向 · {ts}", f"\n⚠️ 错误: {result.get('error', '未知')}"])

        data = result.get("data", {})
        symbol = data.get("symbol") or getattr(intent_obj, "symbol", "?") or "?"
        items = data.get("items", [])

        lines = [f"💰 {symbol} 资金流向 · {ts}", ""]
        if not items:
            lines.extend(["暂无资金流数据", "", "数据源: akshare"])
            return "\n".join(lines)

        latest = items[0] if isinstance(items[0], dict) else {}
        d = _fmt_date(_pick(latest, ["日期", "交易日期", "date"]))
        main_inflow = _pick(latest, ["主力净流入-净额", "主力净流入", "主力净额", "主力净流入额"])
        main_ratio = _pick(latest, ["主力净流入-净占比", "主力净占比", "主力净流入占比"])
        close_price = _pick(latest, ["收盘价", "收盘", "close"])
        pct = _pick(latest, ["涨跌幅", "涨跌幅%"])

        lines.append(
            f"最新({d}): 收盘 {_fmt_price(close_price)} ({_fmt_pct(pct)}) | 主力净流入 {_fmt_amount(main_inflow)} ({_fmt_pct(main_ratio)})"
        )
        lines.append("")
        lines.append("近5日主力净流入:")

        for item in items[:5]:
            if not isinstance(item, dict):
                lines.append(str(item))
                continue
            day = _fmt_date(_pick(item, ["日期", "交易日期", "date"]))
            inflow = _pick(item, ["主力净流入-净额", "主力净流入", "主力净额", "主力净流入额"])
            ratio = _pick(item, ["主力净流入-净占比", "主力净占比", "主力净流入占比"])
            lines.append(f"- {day}: {_fmt_amount(inflow)} ({_fmt_pct(ratio)})")

        lines.extend(["", "数据源: akshare"])
        return _truncate("\n".join(lines), MAX_LEN)

    sections = [
        f"{emoji} A股分析 · {ts}",
    ]

    params = []
    for key in ["symbol", "date", "period", "top_n"]:
        value = getattr(intent_obj, key, None)
        if value is not None:
            params.append(f"{key}={value}")

    if params:
        sections.append(f"参数: {' | '.join(params)}")

    if not result.get("ok"):
        sections.append(f"\n⚠️ 错误: {result.get('error', '未知')}")
        return "\n".join(sections)

    data = result.get("data", {})
    items = data.get("items", [])
    if items:
        for item in items[:5]:
            if isinstance(item, dict):
                name = item.get("名称") or item.get("股票代码") or "未知"
                price = item.get("最新价") or item.get("收盘")
                change = item.get("涨跌幅")
                if price is not None:
                    direction = "📈" if (_safe_float(change) or 0) >= 0 else "📉"
                    change_str = f" ({_fmt_pct(change)})" if change is not None else ""
                    sections.append(f"{direction} {name}: {price}{change_str}")

    if len(items) > 5:
        sections.append(f"... 还有 {len(items)-5} 条")

    sections.append("\n数据源: akshare")
    final = "\n".join(sections)
    return _truncate(final, MAX_LEN)
