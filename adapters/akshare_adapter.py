#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
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
                return data.head(top_n).to_dict(orient="records")
            except Exception:
                return str(data)

        return data

    def _data_len(self, data: Any) -> int:
        try:
            return int(len(data))
        except Exception:
            return 0

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
            from datetime import timedelta

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

        end = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")

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

        trade_date = (date or datetime.now().strftime("%Y%m%d")).replace("-", "")

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

        clean_symbol = symbol.lower().replace("sz", "").replace("sh", "").replace("bj", "")
        market = "sh"
        if clean_symbol.startswith(("0", "3")):
            market = "sz"
        elif clean_symbol.startswith(("8", "4")):
            market = "bj"

        try:
            df = self._ak.stock_individual_fund_flow(stock=clean_symbol, market=market)
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                fn_name,
                symbol=clean_symbol,
                market=market,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            return self._error(fn_name, str(exc))
