import datetime
from abc import abstractmethod
from enum import Enum
from typing import List

import numpy as np
from pyfinance.options import BSM


class Direction(Enum):
    LONG = 1
    SHORT = 2


class Instrument:

    def __init__(self, id=None):
        self.id = id

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

    @abstractmethod
    def value_nominal(self, spot):
        pass


class Option(Instrument):

    @abstractmethod
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date, is_open=True, id=None):
        super().__init__(id)
        self.sigma = sigma
        self.direction = direction
        self.tran_date = tran_date
        self.delivery_date = datetime.timedelta(weeks=length * 48) + tran_date
        self.is_open = is_open
        self.intrate = intrate
        self.length = length
        self.strike = strike
        self.spot = spot

    def exercise(self, spot):
        return self.value_nominal(spot)

    def value_exercise(self, spot, date):
        if date > self.delivery_date:
            return self.exercise(spot)
        else:
            return self.value(spot)


class Put(Option):
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date,  is_open=True, id=None):
        super().__init__(direction, spot, strike, length, intrate, sigma, tran_date,  is_open, id)
        self.priced_option = BSM(S0=spot, K=strike, T=length, r=intrate, sigma=sigma, kind='put')

    def intrinsic_value(self, spot):
        return self.strike - spot

    def value(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        break_even = -self.priced_option.value() / self.strike
        if spot < break_even:
            return dir_multiplier * (np.log(self.strike / spot) + break_even)
        else:
            return dir_multiplier * break_even

    def value_nominal(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        contracts = 100
        value = self.priced_option.value()
        premium = value * contracts * dir_multiplier
        break_even = self.strike - value
        intrinsic_component = ((break_even - spot) * contracts) * dir_multiplier
        if spot < break_even:
            return intrinsic_component - premium
        else:
            return -premium


class Call(Option):
    def __init__(self, direction, spot, strike, length, intrate, sigma, tran_date, is_open=True, id=None):
        super().__init__(direction, spot, strike, length, intrate, sigma, tran_date, is_open, id)
        self.priced_option = BSM(S0=spot, K=strike, T=length, r=intrate, sigma=sigma, kind='call')

    def intrinsic_value(self, spot):
        return spot - self.strike

    def value(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        break_even = -self.priced_option.value() / self.strike
        if spot > self.strike:
            return dir_multiplier * (np.log(spot / self.strike) + break_even)
        else:
            return dir_multiplier * break_even

    def value_nominal(self, spot):
        dir_multiplier = -1 if self.direction is Direction.SHORT else 1
        contracts = 100
        value = self.priced_option.value()
        break_even = self.strike + value
        premium = value * contracts * dir_multiplier
        intrinsic_component = ((spot - break_even) * contracts) * dir_multiplier
        if spot > break_even:
            return intrinsic_component - premium
        else:
            return -premium


class Structure(Instrument):
    def value_nominal(self, spot):
        return sum([v.value_nominal(spot) for v in self.options])

    def __init__(self, options: List[Option], id=None):
        super().__init__(id)
        self.options = options

    def intrinsic_value(self, spot):
        return sum([v.intrinsic_value(spot) for v in self.options])

    def value(self, spot):
        return sum([v.value(spot) for v in self.options])

    def exercise(self, spot):
        return sum([v.exercise(spot) for v in self.options])

    def value_exercise(self, spot, date):
        return sum([v.value_exercise(spot, date) for v in self.options])


class Forward(Instrument):

    def value_nominal(self, spot):
        return self.intrinsic_value(spot)

    def __init__(self, spot, direction, tran_date, length, is_open=True, id=None):
        super().__init__(id)
        self.is_open = is_open
        self.length = length
        self.direction = direction
        self.trade_value = spot
        self.tran_date = tran_date
        self.contra_value = 1 / spot
        self.delivery_date = datetime.timedelta(weeks=length * 48) + tran_date

    def intrinsic_value(self, spot):
        contra_value = spot * self.contra_value
        return contra_value - self.trade_value if self.direction is Direction.LONG else self.trade_value - contra_value

    def value(self, spot):
        return np.log(spot / self.trade_value)

    def exercise(self, spot):
        if self.is_open:
            self.is_open = False
            return self.intrinsic_value(spot)
        else:
            return 0

    def value_exercise(self, spot, date):
        if date > self.delivery_date:
            return self.exercise(spot)
        else:
            return self.value(spot)
