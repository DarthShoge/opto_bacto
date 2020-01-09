from typing import Dict, List
import pandas as pd
from backtest import Portfolio, SimplePortfolio
from instrument import Forward, Direction, Instrument


def passive_market_exposure(data: Dict[str, pd.DataFrame], portfolio: Portfolio) -> List[Instrument]:
    today = next((v for k,v in data.items())).index[-1]
    if not portfolio.positions or any([x for x in portfolio.positions if x.delivery_date == today]):
        ccys = data.keys()
        new_positions = [
            Forward(spot=data[ccy].Spot.iloc[-1],
                    direction=Direction.LONG,
                    tran_date=pd.to_datetime(data[ccy].index[-1]),
                    length= 1 / 12,
                    is_open=True,
                    id=ccy)
            for ccy in ccys]
        return new_positions
    return []
