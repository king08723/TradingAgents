from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.market_data_validator import build_verified_market_snapshot


@tool
def get_verified_market_snapshot(
    symbol: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "the current trading date, YYYY-mm-dd"],
    look_back_days: Annotated[
        int, "number of recent trading rows to include for sanity-checking"
    ] = 30,
) -> str:
    """Deterministic verification snapshot for exact market-data claims.

    Returns the latest OHLCV row on or before curr_date, common technical
    indicators, and recent closes. Call this before making exact claims about
    price levels, Bollinger bands, RSI, MACD, moving averages, support /
    resistance, or historical comparisons, and treat it as the source of truth.
    """
    # 校验快照绕过了 route_to_vendor；空行情必须返回 sentinel，
    # 不能把 NoMarketDataError 抛进 ToolNode，否则整次分析会直接崩溃。
    try:
        return build_verified_market_snapshot(symbol, curr_date, look_back_days)
    except (NoMarketDataError, ValueError) as e:
        return (
            f"NO_DATA_AVAILABLE: cannot build a verified market snapshot for "
            f"'{symbol}' ({e}). Do not estimate or fabricate values — report "
            f"that data is unavailable for this symbol."
        )
