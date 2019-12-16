import datetime
from abc import abstractmethod
from enum import Enum
from typing import List

from pyfinance.options import BSM


class Direction(Enum):
    LONG = 1
    SHORT = 2


class Instrument:

    @abstractmethod
    def intrinsic_value(self, spot):
        pass

    @abstractmethod
    def value(self, spot):
        pass

    @abstractmethod
    def exercise(self, spot):
        pass

    @abstractmethod
    def value_exercise(self, spot, date):
        pass


class Option(Instrument):

    @abstractmethod
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date, contracts, is_open=True):
        self.sigma = sigma
        self.direction = direction
        self.tran_date = tran_date
        self.delivery_date = datetime.timedelta(weeks=length * 48) + tran_date
        self.contracts = contracts
        self.is_open = is_open
        self.intrate = intrate
        self.length = length
        self.strike = strike
        self.spot = spot

    def exercise(self, spot):
        self.is_open = False
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        contracts = self.contracts * 100
        premium = self.priced_option.value() * contracts * dir_multiplier
        return self.value(spot) - premium

    def value_exercise(self, spot, date):
        if date > self.delivery_date:
            return self.exercise(spot)
        else:
            return self.value(spot)


class Put(Option):
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date, contracts, is_open=True):
        super().__init__(direction, spot, strike, length, intrate, sigma, tran_date, contracts, is_open)
        self.priced_option = BSM(S0=spot, K=strike, T=length, r=intrate, sigma=sigma, kind='put')
        self.premium_paid = (contracts * 100) * self.priced_option.value()

    def intrinsic_value(self, spot):
        return self.strike - spot

    def value(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        contracts = self.contracts * 100
        premium = self.priced_option.value() * contracts * dir_multiplier
        break_even = self.strike - self.priced_option.value()
        intrinsic_component = ((break_even - spot) * contracts) * dir_multiplier
        if spot < break_even:
            return intrinsic_component - premium
        else:
            return -premium


class Call(Option):
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date, contracts, is_open=True):
        super().__init__(direction, spot, strike, length, intrate, sigma, tran_date, contracts, is_open)
        self.priced_option = BSM(S0=spot, K=strike, T=length, r=intrate, sigma=sigma, kind='call')
        self.premium_paid = (contracts * 100) * self.priced_option.value()

    def intrinsic_value(self, spot):
        return spot - self.strike

    def value(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        contracts = self.contracts * 100
        break_even = self.strike + self.priced_option.value()
        premium = self.priced_option.value() * contracts * dir_multiplier
        intrinsic_component = ((spot - break_even) * contracts) * dir_multiplier
        if spot > break_even:
            return intrinsic_component - premium
        else:
            return -premium


class Structure(Instrument):
    def __init__(self, options: List[Option]):
        self.options = options

    def intrinsic_value(self, spot):
        return sum([v.intrinsic_value(spot) for v in self.options])

    def value(self, spot):
        return sum([v.value(spot) for v in self.options])

    def exercise(self, spot):
        return sum([v.exercise(spot) for v in self.options])

    def value_exercise(self, spot, date):
        return sum([v.value_exercise(spot, date) for v in self.options])