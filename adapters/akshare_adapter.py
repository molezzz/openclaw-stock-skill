#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class AkshareAdapter:
    def __init__(self) -> None:
        self._ak = None
        self._import_error = None
        try:
            import akshare as ak  # type: ignore

            self._ak = ak
        except Exception as exc:
            self._import_error = str(exc)

    def _wrap(self, fn_name: str, **payload: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "source": "akshare",
            "api": fn_name,
            "data": payload,
        }

    def _error(self, fn_name: str, message: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "source": "akshare",
            "api": fn_name,
            "error": message,
        }

    def _ready_or_error(self, fn_name: str) -> Optional[Dict[str, Any]]:
        if self._ak is None:
            return self._error(fn_name, f"akshare import failed: {self._import_error}")
        return None

    def _to_records(self, data: Any, top_n: int = 10) -> Any:
        if data is None:
            return []

        if hasattr(data, "head") and hasattr(data, "to_dict"):
            try:
                if top_n and top_n > 0:
                    return data.head(top_n).to_dict(orient="records")
                return data.to_dict(orient="records")
            except Exception:
                return str(data)

        return data

    def _data_len(self, data: Any) -> int:
        try:
            return int(len(data))
        except Exception:
            return 0

    def _normalize_trade_date(self, value: Optional[str]) -> str:
        if not value or value in {"today", "今日", "今天"}:
            return datetime.now().strftime("%Y%m%d")
        if value in {"yesterday", "昨日", "昨天"}:
            return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        return str(value).replace("-", "").replace("/", "")

    def _clean_symbol(self, symbol: Optional[str]) -> str:
        if not symbol:
            return ""
        return str(symbol).lower().replace("sz", "").replace("sh", "").replace("bj", "")

    def _market_from_symbol(self, symbol: str) -> str:
        market = "sh"
        if symbol.startswith(("0", "3")):
            market = "sz"
        elif symbol.startswith(("8", "4")):
            market = "bj"
        return market

    def _filter_records_by_symbol(self, records: list[dict], symbol: str) -> list[dict]:
        if not symbol:
            return records

        key_pool = ["代码", "股票代码", "证券代码", "symbol", "代码简称"]
        filtered = []
        for row in records:
            if not isinstance(row, dict):
                continue
            for key in key_pool:
                val = row.get(key)
                if val is not None and symbol in str(val):
                    filtered.append(row)
                    break
        return filtered

    def _call_api_candidates(self, candidates: list[tuple[str, list[dict]]]) -> tuple[Optional[str], Any, str]:
        errors = []

        for fn_name, kwargs_list in candidates:
            func = getattr(self._ak, fn_name, None)
            if func is None:
                continue

            args_pool = kwargs_list or [{}]
            for kwargs in args_pool:
                try:
                    result = func(**kwargs)
                    return fn_name, result, ""
                except Exception as exc:
                    errors.append(f"{fn_name}({kwargs}): {exc}")

        return None, None, "; ".join(errors) if errors else "no callable api found"

    def index_spot(self, top_n: int = 300) -> Dict[str, Any]:
        primary_fn = "stock_zh_index_spot_sina"
        err = self._ready_or_error(primary_fn)
        if err:
            return err

        try:
            df = self._ak.stock_zh_index_spot_sina()
            return self._wrap(primary_fn, items=self._to_records(df, top_n=top_n))
        except Exception as exc:
            fallback_fn = "stock_zh_index_spot_em"
            try:
                df = self._ak.stock_zh_index_spot_em()
                return self._wrap(fallback_fn, items=self._to_records(df, top_n=top_n))
            except Exception as fallback_exc:
                return self._error(primary_fn, f"sina failed: {exc}; em failed: {fallback_exc}")

    def stock_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        top_n: int = 60,
    ) -> Dict[str, Any]:
        fn_name = "stock_zh_a_hist"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        if not start_date:
            end_dt = datetime.now()
            if period == "weekly":
                days = top_n * 7
            elif period == "monthly":
                days = top_n * 30
            else:
                days = top_n
            start_dt = end_dt - timedelta(days=days + 50)
            start = start_dt.strftime("%Y%m%d")
        else:
            start = start_date.replace("-", "")

        end = self._normalize_trade_date(end_date)

        try:
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust="",
            )
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                fn_name,
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def stock_intraday(self, symbol: str, period: Optional[str] = None, top_n: int = 30) -> Dict[str, Any]:
        fn_name = "stock_intraday"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        minute_error = None
        minute_period = period if period in {"1", "5", "15", "30", "60"} else "1"

        try:
            df = self._ak.stock_zh_a_minute(symbol=symbol, period=minute_period, adjust="")
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                "stock_zh_a_minute",
                symbol=symbol,
                period=minute_period,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            minute_error = str(exc)

        try:
            df = self._ak.stock_intraday_em(symbol=symbol)
            return self._wrap(
                "stock_intraday_em",
                symbol=symbol,
                period="tick",
                fallback=minute_error,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            if minute_error:
                return self._error(fn_name, f"minute failed: {minute_error}; tick failed: {exc}")
            return self._error(fn_name, str(exc))

    def limit_pool(self, date: Optional[str] = None, top_n: int = 50) -> Dict[str, Any]:
        fn_name = "stock_zt_pool_em"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        trade_date = self._normalize_trade_date(date)

        try:
            up_df = self._ak.stock_zt_pool_em(date=trade_date)
            up_count = self._data_len(up_df)
            up_items = self._to_records(up_df, top_n=top_n)

            down_count = 0
            down_items: Any = []
            down_api = None
            down_errors = []

            for api_name in ["stock_zt_pool_dtgc_em", "stock_dt_pool_em"]:
                func = getattr(self._ak, api_name, None)
                if func is None:
                    continue
                try:
                    down_df = func(date=trade_date)
                    down_count = self._data_len(down_df)
                    down_items = self._to_records(down_df, top_n=top_n)
                    down_api = api_name
                    break
                except Exception as exc:
                    down_errors.append(f"{api_name}: {exc}")

            payload: Dict[str, Any] = {
                "date": trade_date,
                "up_count": up_count,
                "down_count": down_count,
                "up_items": up_items,
                "down_items": down_items,
                "items": up_items,
            }
            if down_api:
                payload["down_api"] = down_api
            if down_errors and not down_api:
                payload["down_error"] = "; ".join(down_errors)

            return self._wrap(fn_name, **payload)
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def money_flow(self, symbol: str, top_n: int = 30) -> Dict[str, Any]:
        fn_name = "stock_individual_fund_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)
        market = self._market_from_symbol(clean_symbol)

        try:
            df = self._ak.stock_individual_fund_flow(stock=clean_symbol, market=market)
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                fn_name,
                scope="individual",
                symbol=clean_symbol,
                market=market,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def market_money_flow(self, top_n: int = 20, date: Optional[str] = None) -> Dict[str, Any]:
        fn_name = "market_money_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        trade_date = self._normalize_trade_date(date)

        candidates = [
            ("stock_market_fund_flow", [{}]),
            ("stock_hsgt_fund_flow_summary_em", [{}]),
            ("stock_hsgt_north_net_flow_in_em", [{}]),
            ("stock_hsgt_hist_em", [{"symbol": "北向资金"}, {"symbol": "沪股通"}, {"symbol": "深股通"}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        if hasattr(df, "iloc"):
            try:
                df = df.iloc[::-1]
            except Exception:
                pass

        return self._wrap(
            api_name or fn_name,
            scope="market",
            date=trade_date,
            items=self._to_records(df, top_n=top_n),
        )

    def sector_money_flow(self, top_n: int = 20) -> Dict[str, Any]:
        fn_name = "sector_money_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        candidates = [
            (
                "stock_sector_fund_flow_rank",
                [
                    {"indicator": "今日", "sector_type": "行业资金流"},
                    {"indicator": "5日", "sector_type": "行业资金流"},
                    {"indicator": "10日", "sector_type": "行业资金流"},
                    {"symbol": "今日", "sector_type": "行业资金流"},
                    {"sector_type": "行业资金流"},
                ],
            ),
            ("stock_fund_flow_industry", [{"symbol": "今日"}, {"symbol": "即时"}, {}]),
            ("stock_sector_fund_flow_summary", [{"sector_type": "行业资金流"}, {}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        return self._wrap(
            api_name or fn_name,
            scope="sector",
            items=self._to_records(df, top_n=top_n),
        )

    def fundamental(self, symbol: str, top_n: int = 20) -> Dict[str, Any]:
        fn_name = "fundamental"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)

        candidates = [
            (
                "stock_financial_abstract_ths",
                [
                    {"symbol": clean_symbol, "indicator": "按报告期"},
                    {"symbol": clean_symbol, "indicator": "按单季度"},
                    {"symbol": clean_symbol},
                    {"stock": clean_symbol, "indicator": "按报告期"},
                    {"stock": clean_symbol},
                ],
            ),
            (
                "stock_financial_analysis_indicator",
                [
                    {"symbol": clean_symbol},
                    {"stock": clean_symbol},
                ],
            ),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        if hasattr(df, "iloc"):
            try:
                df = df.iloc[::-1]
            except Exception:
                pass

        items = self._to_records(df, top_n=top_n)
        latest = items[0] if isinstance(items, list) and items else {}

        return self._wrap(
            api_name or fn_name,
            scope="fundamental",
            symbol=clean_symbol,
            latest=latest,
            items=items,
        )

    def margin_lhb(self, symbol: Optional[str] = None, date: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        fn_name = "margin_lhb"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)
        trade_date = self._normalize_trade_date(date)

        margin_candidates = [
            (
                "stock_margin_detail",
                [
                    {"date": trade_date, "symbol": clean_symbol},
                    {"date": trade_date, "stock": clean_symbol},
                    {"date": trade_date, "code": clean_symbol},
                    {"date": trade_date},
                ],
            ),
            ("stock_margin_detail_em", [{"date": trade_date}, {"trade_date": trade_date}, {}]),
            ("stock_margin_underlying_info_szse", [{}]),
            ("stock_margin_underlying_info_sse", [{}]),
        ]

        margin_api, margin_df, margin_err = self._call_api_candidates(margin_candidates)
        margin_items: list[dict] = []
        if margin_df is not None:
            margin_items = self._to_records(margin_df, top_n=0)
            if isinstance(margin_items, list):
                margin_items = [item for item in margin_items if isinstance(item, dict)]
                margin_items = self._filter_records_by_symbol(margin_items, clean_symbol)
                margin_items = margin_items[:top_n]
            else:
                margin_items = []

        lhb_candidates = [
            (
                "stock_lhb_detail_em",
                [
                    {"start_date": trade_date, "end_date": trade_date},
                    {"date": trade_date},
                    {},
                ],
            ),
            ("stock_lhb_ggtj_sina", [{"symbol": "5"}, {"symbol": "10"}, {}]),
        ]

        lhb_api, lhb_df, lhb_err = self._call_api_candidates(lhb_candidates)
        lhb_items: list[dict] = []
        if lhb_df is not None:
            lhb_items = self._to_records(lhb_df, top_n=0)
            if isinstance(lhb_items, list):
                lhb_items = [item for item in lhb_items if isinstance(item, dict)]
                lhb_items = self._filter_records_by_symbol(lhb_items, clean_symbol)
                lhb_items = lhb_items[:top_n]
            else:
                lhb_items = []

        if margin_df is None and lhb_df is None:
            return self._error(fn_name, f"margin failed: {margin_err}; lhb failed: {lhb_err}")

        return self._wrap(
            fn_name,
            scope="margin_lhb",
            symbol=clean_symbol,
            date=trade_date,
            margin_api=margin_api,
            lhb_api=lhb_api,
            margin_items=margin_items,
            lhb_items=lhb_items,
            margin_error=margin_err if margin_df is None else None,
            lhb_error=lhb_err if lhb_df is None else None,
        )
