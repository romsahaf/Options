from dataclasses import dataclass
import pandas as pd
import datetime
from TradeObjects import *
from typing import List
import statistics as st
from collections import OrderedDict


def is_inside_bar(curr_bar: Bar, prev_bar: Bar):
    # Checks if current bar is an inside-bar
    return curr_bar.high < prev_bar.high and curr_bar.low > prev_bar.low


def is_outside_bar(curr_bar: Bar, prev_bar: Bar):
    return curr_bar.high > prev_bar.high and curr_bar.low < prev_bar.low


def get_bar(stock: OrderedDict, start_date: datetime, end_date: datetime, permno, num_of_weeks):
    data = get_data_between_dates(stock, start_date, end_date)
    if len(data) < 3 * num_of_weeks:
        return None
    bar_start_date = start_date
    first_open = data[0].open
    last_close = data[-1].close
    highest_high = max(map(lambda d: d.high, data))
    lowest_low = min(map(lambda d: d.low, data))
    average_volume = sum(map(lambda d: d.volume, data)) / len(data)
    return Bar(bar_start_date, first_open, last_close, highest_high, lowest_low, average_volume)


def get_data_between_dates(stock, start_date: datetime, end_date: datetime) -> List[DayData]:
    data = []
    date = start_date
    while date <= end_date:
        if stock[date] is not None and 0 <= date.weekday() <= 4:
            data.append(stock[date])
        date += datetime.timedelta(days=1)
    return data


def print_stats(trades_df):
    trades_num = len(trades_df)
    return_ratios = list(map(lambda s: float(s.strip('%')) / 100, trades_df['Return_Ratio'].tolist()))
    print("Average Percentage: {}%".format(round(sum(return_ratios) * 100 / trades_num, 2)))
    print("Standard Deviation: {}%".format(round(st.stdev(return_ratios) * 100, 2)))
    print("Trades: {}".format(trades_num))
    pos_returns = [return_ratio for return_ratio in return_ratios if return_ratio > 0]
    neg_returns = [abs(return_ratio) for return_ratio in return_ratios if return_ratio < 0]
    print("Positives: {}".format(len(pos_returns)))
    print("Negatives: {}".format(len(neg_returns)))
    pos_return_ratio = sum(pos_returns) / len(pos_returns)
    neg_return_ratio = sum(neg_returns) / len(neg_returns)
    print("Positive Average: {}%".format(round(pos_return_ratio * 100, 2)))
    print("Negative Average: {}%".format(round(neg_return_ratio * 100, 2)))
    risk_return_ratio = round(pos_return_ratio / neg_return_ratio, 2)
    print("Risk Return Ratio: {}".format(risk_return_ratio))
    print("Expectancy: {}%".format(round(((1 + risk_return_ratio) * (len(pos_returns) / trades_num) - 1) * 100, 2)))
