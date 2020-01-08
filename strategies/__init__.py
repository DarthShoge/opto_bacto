from typing import Dict
import pandas as pd
from backtest import Portfolio, SimplePortfolio
from instrument import Forward, Direction


def passive_market_exposure(data: Dict[str, pd.DataFrame], portfolio: Portfolio):
    if not portfolio.positions:
        ccys = data.keys()
        new_positions = [
            Forward(spot=data[ccy].Spot.iloc[-1],
                    direction=Direction.LONG,
                    tran_date=pd.to_datetime(data[ccy].index[-1]),
                    length= 6 / 12,
                    is_open=True,
                    id=ccy)
            for ccy in ccys]
        return new_positions
    return []
