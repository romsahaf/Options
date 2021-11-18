import datetime
import sys
from time import perf_counter

from SignalsBuilder import *
from TradeObjects import *

counter_start = perf_counter()  # for performance-timing purpose


def back_test_run():
    # Check if Trades file is not already open
    trades_file = None
    try:
        trades_file = pd.read_csv("Options Trades.csv")
    except FileNotFoundError:
        pass
    if trades_file is not None:
        trades_file.to_csv('Options Trades.csv', index=False, header=True)

    print("Starting Options Back Test Run")
    counter = 0
    trades = {'Permno': [], 'Symbol': [], 'Buy_Date': [], 'Sell_Date': [], 'Buy_Price': [], 'Sell_Price': [],
              'Return_Ratio': [], 'Bar_Volume': [], 'Bar_Type': []}

    stocks_permnos = pd.read_csv("Stocks csv files/Permnos.csv").Permno.tolist()
    permno_to_symbol = pd.read_csv("Stocks csv files/Permno_to_symbol.csv")
    permno_match = permno_to_symbol["PERMNO"].tolist()
    symbol_match = permno_to_symbol["HTSYMBOL"].tolist()

    # Debug code
    permno = 14593

    # e.g. datetime.date(1993, 3, 26)
    debug_date = datetime.date(2018, 12, 21)

    debug_mode = getattr(sys, 'gettrace', lambda: None)() is not None
    print("Debug Mode") if debug_mode else None
    # Debug code

    if debug_mode and permno is not None and debug_date is not None:
        stocks_permnos = [permno]

    # Number of weeks for strategy
    num_of_weeks = 1

    ########################################################################################################################
    # Main back test loop
    ########################################################################################################################

    for permno in stocks_permnos:
        try:
            symbol = symbol_match[permno_match.index(permno)]
        except ValueError:
            symbol = "NA"

        stock_data = pd.read_csv("Stocks csv files/{}.csv".format(permno))
        stock = list(map(lambda row: DayData(row[0], row[1], row[2], row[3], row[4], row[5]), stock_data.values))

        trading_state = TradingState.Hunting
        order = None
        option = None

        for curr_day_index in range(40, len(stock)):

            curr_day = stock[curr_day_index]
            # Debug code
            if debug_mode and curr_day.date == debug_date:
                print("stop")
            # Debug code

            # We bought the stock (an order has been executed):
            if trading_state == TradingState.InPortfolio:
                if option.type == "call":
                    if curr_day.low <= option.stop_loss:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.open if curr_day.open < option.stop_loss else option.stop_loss, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    elif curr_day.high >= option.target:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.open if curr_day.open > option.target else option.target, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    if option is not None and curr_day.date.weekday() >= 4:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.close, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                else:  # option is "put"
                    if curr_day.high >= option.stop_loss:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.open if curr_day.open > option.stop_loss else option.stop_loss, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    elif curr_day.low <= option.target:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.open if curr_day.open < option.target else option.target, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    if option is not None and curr_day.date.weekday() >= 4:
                        add_trade(trades, permno, symbol, curr_day, option, curr_day.close, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting

            # We're waiting for an order to be executed:
            elif trading_state == TradingState.PendingOrder:
                if (curr_day.date - order.date).days <= 4:
                    if curr_day.open <= order.call < curr_day.high:
                        option = Option(curr_day.date, "call", order.call, order.call + (order.call - order.call_stop_loss) * 2, order.call_stop_loss)
                        trading_state = TradingState.InPortfolio
                    elif curr_day.open >= order.put > curr_day.low:
                        option = Option(curr_day.date, "put", order.put, order.put - (order.put_stop_loss - order.put) * 2, order.put_stop_loss)
                        trading_state = TradingState.InPortfolio
                else:
                    trading_state = TradingState.Hunting
                    order = None

            # We're hunting for the right conditions:
            if trading_state == TradingState.Hunting:
                # yearly_vol = [dd.volume for dd in stock[max(curr_day_index - 253, 0):curr_day_index + 1]]
                # if sum(yearly_vol) / len(yearly_vol) < 1000000:
                #     continue
                if curr_day.date.weekday() == 4:  # Check if current date is friday
                    curr_bar = get_weeks_bar(stock, curr_day_index, num_of_weeks)
                    prev_bar = get_weeks_bar(stock, curr_day_index - 5 * num_of_weeks, num_of_weeks)
                    if curr_bar is None or prev_bar is None:
                        continue
                    inside_bar, outside_bar = is_inside_bar(curr_bar, prev_bar), is_outside_bar(curr_bar, prev_bar)
                    if inside_bar or outside_bar:
                        fibo_call = curr_bar.high - (curr_bar.high - curr_bar.low) * 0.618
                        fibo_put = curr_bar.low + (curr_bar.high - curr_bar.low) * 0.618
                        order = Order(curr_day.date, curr_bar.high, curr_bar.low, fibo_call, fibo_put, curr_bar.volume, "IB" if inside_bar else "OB")
                        trading_state = TradingState.PendingOrder

        counter += 1
        percent = round(len(stocks_permnos) / 100)
        if percent > 0 and counter % percent == 0:
            print("\rFinished {}% of stocks...".format(round(counter / percent)), end="")

    trades_df = pd.DataFrame(trades, columns=list(trades.keys()))
    trades_df = trades_df.sort_values(['Buy_Date', 'Permno']).reset_index(
        drop=True)  # sorts the trades by buy date
    trades_df.to_csv('Options Trades.csv', index=False, header=True)
    print("\nDone in {:.0f} seconds! See Trades.csv".format(perf_counter() - counter_start))

    print_stats(trades_df)


def add_trade(trades, permno, symbol, curr_day, option, sell_price, sign, bar_vol, bar_type):
    trades['Permno'].append(permno)
    trades['Symbol'].append(symbol)
    trades['Buy_Date'].append(option.buy_date)
    trades['Buy_Price'].append(option.buy_price)
    trades['Sell_Date'].append(curr_day.date)
    trades['Sell_Price'].append(sell_price)
    trade_return = sign * (sell_price - option.buy_price) / option.buy_price
    trades['Return_Ratio'].append(str(round(100 * trade_return, 2)) + '%')
    trades['Bar_Volume'].append(bar_vol)
    trades['Bar_Type'].append(bar_type)


if __name__ == '__main__':
    back_test_run()
