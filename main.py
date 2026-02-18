#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from typing import Any, Dict

from adapters import AkshareAdapter
from formatter import render_output
from router import (
    FUNDAMENTAL,
    INDEX_REALTIME,
    INTRADAY_ANALYSIS,
    KLINE_ANALYSIS,
    LIMIT_STATS,
    MARGIN_LHB,
    MONEY_FLOW,
    parse_query,
)


def dispatch(intent_obj, adapter: AkshareAdapter) -> Dict[str, Any]:
    if intent_obj.intent == INDEX_REALTIME:
        return adapter.index_spot(top_n=300)

    if intent_obj.intent == KLINE_ANALYSIS:
        top_n = intent_obj.top_n or 10
        symbol = intent_obj.symbol or "000001"
        period = intent_obj.period or "daily"
        return adapter.stock_kline(symbol=symbol, period=period, top_n=top_n)

    if intent_obj.intent == INTRADAY_ANALYSIS:
        top_n = intent_obj.top_n or 30
        symbol = intent_obj.symbol or "000001"
        period = intent_obj.period if intent_obj.period in {"1", "5", "15", "30", "60"} else "1"
        return adapter.stock_intraday(symbol=symbol, period=period, top_n=top_n)

    if intent_obj.intent == LIMIT_STATS:
        top_n = intent_obj.top_n or 20
        return adapter.limit_pool(date=intent_obj.date, top_n=top_n)

    if intent_obj.intent == MONEY_FLOW:
        top_n = intent_obj.top_n or 10
        query = intent_obj.query or ""
        if any(k in query for k in ["北向", "南向", "东向", "市场资金", "大盘资金"]):
            return adapter.market_money_flow(top_n=top_n, date=intent_obj.date)
        if any(k in query for k in ["行业资金", "板块资金", "行业流入", "板块流入"]):
            return adapter.sector_money_flow(top_n=top_n)
        symbol = intent_obj.symbol or "000001"
        return adapter.money_flow(symbol=symbol, top_n=top_n)

    if intent_obj.intent == FUNDAMENTAL:
        top_n = intent_obj.top_n or 20
        symbol = intent_obj.symbol or "600519"
        return adapter.fundamental(symbol=symbol, top_n=top_n)

    if intent_obj.intent == MARGIN_LHB:
        top_n = intent_obj.top_n or 10
        return adapter.margin_lhb(symbol=intent_obj.symbol, date=intent_obj.date, top_n=top_n)

    return {
        "ok": True,
        "source": "framework",
        "message": "该意图已识别，当前阶段先返回基础占位结果",
        "intent": intent_obj.intent,
        "parsed": {
            "symbol": intent_obj.symbol,
            "date": intent_obj.date,
            "period": intent_obj.period,
            "top_n": intent_obj.top_n,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="A股分析 Skill 基础框架")
    parser.add_argument("--query", required=True, help="自然语言请求，例如：分析 600519 最近 30 天 K线")
    parser.add_argument("--platform", default="qq", choices=["qq", "telegram"], help="输出平台")
    args = parser.parse_args()

    intent_obj = parse_query(args.query)
    adapter = AkshareAdapter()
    result = dispatch(intent_obj, adapter)
    output = render_output(intent_obj, result, platform=args.platform)
    print(output)


if __name__ == "__main__":
    main()
