#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import re


INDEX_REALTIME = "INDEX_REALTIME"
KLINE_ANALYSIS = "KLINE_ANALYSIS"
INTRADAY_ANALYSIS = "INTRADAY_ANALYSIS"
LIMIT_STATS = "LIMIT_STATS"
MONEY_FLOW = "MONEY_FLOW"
FUNDAMENTAL = "FUNDAMENTAL"
STOCK_OVERVIEW = "STOCK_OVERVIEW"
MARGIN_LHB = "MARGIN_LHB"
SECTOR_ANALYSIS = "SECTOR_ANALYSIS"
DERIVATIVES = "DERIVATIVES"
FUND_BOND = "FUND_BOND"
HK_US_MARKET = "HK_US_MARKET"


# Common A-share stock aliases for quick name-to-symbol routing.
# Keep this list lightweight and focused on frequently queried names.
STOCK_NAME_MAP = {
    "贵州茅台": "600519",
    "茅台": "600519",
    "宁德时代": "300750",
    "比亚迪": "002594",
    "五粮液": "000858",
    "招商银行": "600036",
    "中国平安": "601318",
    "隆基绿能": "601012",
    "药明康德": "603259",
    "美的集团": "000333",
    "格力电器": "000651",
}


@dataclass
class IntentObj:
    intent: str
    query: str
    symbol: Optional[str] = None
    date: Optional[str] = None
    period: Optional[str] = None
    top_n: Optional[int] = None


def _extract_symbol(query: str) -> Optional[str]:
    m = re.search(r"\b(?:sh|sz)?(\d{6})\b", query.lower())
    if m:
        return m.group(1)

    for name in sorted(STOCK_NAME_MAP, key=len, reverse=True):
        if name in query:
            return STOCK_NAME_MAP[name]

    m = re.search(r"\b(hk\d{4,5}|[A-Z]{1,5})\b", query)
    if m:
        return m.group(1)

    return None


def _extract_date(query: str) -> Optional[str]:
    m = re.search(r"(\d{4})[-/]?(\d{2})[-/]?(\d{2})", query)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    if "今天" in query or "今日" in query:
        return datetime.now().strftime("%Y-%m-%d")
    if "昨天" in query or "昨日" in query:
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    return None


def _extract_period(query: str) -> Optional[str]:
    q = query.lower()
    if "1m" in q or "1分钟" in query:
        return "1"
    if "5m" in q or "5分钟" in query:
        return "5"
    if "15m" in q or "15分钟" in query:
        return "15"
    if "30m" in q or "30分钟" in query:
        return "30"
    if "60m" in q or "60分钟" in query:
        return "60"
    if "周线" in query or "week" in q:
        return "weekly"
    if "月线" in query or "month" in q:
        return "monthly"
    if "日线" in query or "day" in q or "daily" in q:
        return "daily"

    return None


def _extract_top_n(query: str) -> Optional[int]:
    m = re.search(r"top\s*(\d+)", query.lower())
    if m:
        return int(m.group(1))

    m = re.search(r"前\s*(\d+)\s*(名|条|个)?", query)
    if m:
        return int(m.group(1))
    
    # 支持"近N日"、"最近N天"等
    m = re.search(r"近\s*(\d+)\s*(日|天|周|月)", query)
    if m:
        return int(m.group(1))
    m = re.search(r"最近\s*(\d+)\s*(日|天|周|月)", query)
    if m:
        return int(m.group(1))

    return None


def _classify_intent(query: str) -> str:
    q = query.lower()

    if any(k in query for k in ["涨停", "跌停", "涨跌停"]):
        return LIMIT_STATS
    if any(k in query for k in ["分时", "盘口", "逐笔"]):
        return INTRADAY_ANALYSIS
    if any(k in query for k in ["k线", "K线", "日线", "周线", "月线"]) or "kline" in q:
        return KLINE_ANALYSIS
    if any(k in query for k in ["怎么样", "分析", "看下", "评估", "综合"]):
        return STOCK_OVERVIEW
    if any(k in query for k in ["资金流", "主力资金", "北向资金", "南向资金", "东向资金", "行业资金", "板块资金"]):
        return MONEY_FLOW
    if any(k in query for k in ["基本面", "财报", "财务", "市盈率", "市净率", "估值", "roe", "ROE", "毛利率", "净利率", "资产负债率"]):
        return FUNDAMENTAL
    if any(k in query for k in ["融资融券", "龙虎榜", "两融", "融资余额", "融券余额"]):
        return MARGIN_LHB

    if any(k in query for k in ["港股", "美股", "纳斯达克", "道琼斯", "标普", "恒生", "恒指"]) or any(k in q for k in ["nasdaq", "dow", "sp500", "s&p", "hang seng", "hk", "us"]):
        return HK_US_MARKET
    if any(k in query for k in ["期货", "期权", "衍生品", "主力合约", "if", "ih", "ic", "im"]):
        return DERIVATIVES
    if any(k in query for k in ["基金", "净值", "可转债", "转债", "债券", "etf", "ETF"]):
        return FUND_BOND
    if any(k in query for k in ["板块", "行业", "概念", "题材", "轮动", "涨幅榜", "跌幅榜"]):
        return SECTOR_ANALYSIS

    if any(k in query for k in ["大盘", "指数", "上证", "深证", "创业板", "实时"]):
        return INDEX_REALTIME

    return INDEX_REALTIME


def parse_query(query: str) -> IntentObj:
    query = (query or "").strip()
    return IntentObj(
        intent=_classify_intent(query),
        query=query,
        symbol=_extract_symbol(query),
        date=_extract_date(query),
        period=_extract_period(query),
        top_n=_extract_top_n(query),
    )
