from copy import deepcopy
from itertools import groupby
from typing import List, Callable, Dict

import pandas as pd

from instrument import Instrument


class Portfolio:
    def __init__(self, positions: List[Instrument] = None):
        self.__positions = positions or []
        self.attribution ={}
        self.value_history = {}

    @property
    def positions(self):
        # returns immutable list but #NOTE underlying items can still be changed so beware
        return tuple(self.__positions) if self.__positions is not None else ()

    def value(self, id, spot, positions : List[Instrument]):
        # Maybe I should validate new positions at this point
        last_attribution = list(self.attribution.values())[-1] if self.attribution else []
        attribution_sum = sum([x.value(spot) for x in positions])
        return attribution_sum if not last_attribution else attribution_sum - sum([v[id]for k,v in self.attribution.items()])

    def value_all(self, spot_dict, new_positions):
        transaction_costs = self.__apply_transaction_costs(new_positions)
        self.__positions = self.__positions + new_positions
        position_dict = {k: list(g) for k, g in groupby(self.positions, lambda p: p.id)}
        date = next((y for x, y in spot_dict.items())).index[-1]
        slice_attribution = {inst_id: self.value(id=inst_id,
                                                 spot=spot_dict[inst_id].Spot.iloc[-1],
                                                 positions=positions) for
                             inst_id, positions in position_dict.items()}
        self.attribution[date] = (slice_attribution)
        ptfolio_sum = sum([v for k, v in slice_attribution.items()])
        ptfolio_new_value = ptfolio_sum + transaction_costs
        self.__close_out_expired_positions(date)
        self.value_history[date] = ptfolio_new_value
        return ptfolio_new_value

    def __apply_transaction_costs(self, new_positions):
        return 0

    def __close_out_expired_positions(self, date):
        inexpired_positions = [p for p in self.__positions if date <= p.delivery_date]
        self.__positions = inexpired_positions


class SimplePortfolio(Portfolio):
    def __init__(self, counter=0):
        super().__init__()
        self.counter = counter


def expand_through_array(arr, start=0):
    arr_size = len(arr)
    i = start
    while i < arr_size:
        i += 1
        yield arr[start: i]


def recursive_expand(arr, func, end=1, carry=None):
    if end <= len(arr):
        new_carry = func(arr[0:end], carry)
        yield new_carry
        yield from recursive_expand(arr, func, end + 1, new_carry)


def expand_through_time(df_dict, strat, seed_portfolio: Portfolio = None):
    def expand_func(ccy_df_dict: Dict[str, pd.DataFrame],
                    dates: List[pd.datetime],
                    portfolio: Portfolio,
                    strategy: Callable[[Dict[str, pd.DataFrame], Portfolio], List[Instrument]]):
        if not portfolio:
            portfolio = seed_portfolio or Portfolio()
        data_for_slice = {k: v.loc[dates, :] for k, v in ccy_df_dict.items()}
        new_positions = strategy(data_for_slice, portfolio)
        portfolio_value = portfolio.value_all(data_for_slice, new_positions)
        return portfolio

    example = next((y for x, y in df_dict.items()))
    # expanding_dates = [x for x in expand_through_array(example.index)]
    results = [x for x in recursive_expand(example.index, lambda x, y: expand_func(df_dict, x, y, strat))]
    return results[-1]
