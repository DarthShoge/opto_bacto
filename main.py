from datetime import datetime

import matplotlib.pyplot as plt

import numpy as np
import pyodbc
import pandas as pd
from pyfinance.options import BSM

from backtest import Portfolio, expand_through_time
from instrument import Instrument, Call, Direction
from strategies import passive_market_exposure


def extract_ccy(ccy, df_, contract_len=21):
    ccy_df = df_[df_.CurrencyPair == ccy]
    ccy_df.index = ccy_df.ReferenceDate
    ccy_df.drop(['CurrencyPair', 'ReferenceDate'], axis=1, inplace=True)
    ccy_df['Returns'] = np.log(ccy_df.Spot) - np.log(ccy_df.Spot.shift(1))
    ccy_df['RealisedVol'] = (ccy_df.Returns.rolling(contract_len).std() * np.sqrt(252 / contract_len)) * 100
    return ccy_df


def get_all_data(conn_str='DRIVER=SQL Server;SERVER=SQLINT;DATABASE=SMW', from_date=None):
    with pyodbc.connect(conn_str) as con:
        df = pd.read_sql('''SELECT mds.ReferenceDate, ci.CurrencyPair, ci.Spot, ci.ImpliedVol, 
                            ci.Butterfly, ci.RiskRev FROM dbo.CalcInput ci 
                            JOIN dbo.MarketDataSet mds ON mds.Id = ci.MarketDataSetId AND mds.IsMaster = 1''', con,parse_dates=['ReferenceDate'])

        if from_date:
            df = df[df.ReferenceDate >= from_date]

        all_ccys = set(df.CurrencyPair.values)
        df_dict = {ccy: extract_ccy(ccy, df) for ccy in all_ccys}
        return df_dict


def calculate_expected_price_change(spot, vols, std_devs=1, periods=12):
    """
    Calculates the expected price change given a volatility measure. where
    spot: spot prices for instrument
    vols: vol measure be it implied or realised
    st_dev: vols are stddev measure so this changes the price change to be n standard devs off
    """
    pct_vol = vols / 100
    return spot * ((pct_vol * std_devs) / np.sqrt(periods))


def rank(ser, periods=100):
    pctrank = lambda x: pd.Series(x).rank(pct=True).iloc[-1]
    return ser.rolling(periods).apply(pctrank)


def get_option_chain(spot, sigma, kind='call', risk_free_rate=0, granularity=30,
                     contract_length=1 / 12):
    corrected_sigma = (sigma / 100) * -1 if kind != 'call' else (sigma / 100)
    expected_change = spot * (corrected_sigma)
    bound = spot + expected_change
    incr = expected_change / granularity
    price_range = np.arange(spot, bound, incr)
    option_chain = pd.DataFrame(
        BSM(S0=spot, K=price_range, T=contract_length, r=risk_free_rate, sigma=abs(corrected_sigma),
            kind=kind).summary())
    option_chain.index = price_range
    return option_chain


def calculate_25_delta_put_implied_vol(bfly_25, risk_rev, atm_imp_vol):
    return ((bfly_25 - risk_rev) + 2 * atm_imp_vol) / 2


def calculate_25_delta_call_implied_vol(bfly_25, risk_rev, atm_imp_vol):
    return calculate_25_delta_put_implied_vol(bfly_25, risk_rev, atm_imp_vol) + risk_rev


def process_ccy(ccy_df):
    ccy_df['Put_25_Vol'] = calculate_25_delta_put_implied_vol(ccy_df.Butterfly, ccy_df.RiskRev, ccy_df.ImpliedVol)
    ccy_df['Call_25_Vol'] = calculate_25_delta_call_implied_vol(ccy_df.Butterfly, ccy_df.RiskRev, ccy_df.ImpliedVol)
    return 1 + 1


def interpolate_vol_space(delta, vol_space, delta_space):
    delta_space[0] = -50 - delta_space[0]
    delta_space[-1] = 50 - delta_space[-1]
    delta_translate = max(-50 - delta, delta_space[0]) if delta < 0 else min(50 - delta, delta_space[-1])
    poly = np.poly1d(np.polyfit(delta_space, vol_space, deg=2))
    return poly(delta_translate), poly


def plot_payoff(x: Instrument, upper, lower, incr=0.5):
    prices = np.arange(upper, lower, incr)
    inst_values = [x.value(v) for v in prices]
    zero = [0 for v in prices]
    plt.plot(prices, inst_values)
    plt.plot(prices, zero)
    plt.show()


# interpolate_vol_space(-10,[4.71,4.48,5.23],[-5,0,5])
op1 = Call(direction=Direction.SHORT,
           spot=1.10,
           strike=1.12,
           length=1/12,
           intrate= 0.01,
           sigma=0.1,
           tran_date=datetime.now())
data = get_all_data(from_date='2018-12-01')
ptflo = expand_through_time(data, passive_market_exposure, Portfolio())
process_ccy(data['EURUSD'])


def main():
    fx_df_dict = get_all_data()