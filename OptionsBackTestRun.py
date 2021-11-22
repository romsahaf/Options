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
    permno = None
    # e.g. datetime.date(1993, 3, 26)
    debug_date = None

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
        stock = OrderedDict()
        start_date = datetime.date(*list(map(int, stock_data.iloc[0]["Date"].split('-'))))
        end_date = datetime.date(*list(map(int, stock_data.iloc[-1]["Date"].split('-'))))
        date = start_date
        # fills stock dictionary with all dates from start_date to end_date
        while date <= end_date:
            stock[date] = None
            date += datetime.timedelta(days=1)
        # fills stock dictionary with all days' data from the dataFrame
        for row in stock_data.values:
            date = datetime.date(*list(map(int, row[0].split('-'))))
            stock[date] = DayData(row[1], row[2], row[3], row[4], row[5])
        # Skipping to the first weekend
        for date in stock:
            if date.weekday() == 4:
                start_date = date
                break

        trading_state = TradingState.Hunting
        order = None
        option = None

        for curr_date in stock:
            if (curr_date - start_date).days <= 14 * num_of_weeks:
                continue

            curr_day_data = stock[curr_date]

            # Debug code
            if debug_mode and curr_date == debug_date:
                print("stop")
            # Debug code

            # We bought the stock (an order has been executed):
            if trading_state == TradingState.InPortfolio:
                if stock[curr_date] is None:
                    continue
                if option.type == "call":
                    if curr_day_data.low <= option.stop_loss:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.open if curr_day_data.open < option.stop_loss else option.stop_loss, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    elif curr_day_data.high >= option.target:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.open if curr_day_data.open > option.target else option.target, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    if option is not None and curr_date.weekday() >= 4:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.close, 1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                else:  # option is "put"
                    if curr_day_data.high >= option.stop_loss:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.open if curr_day_data.open > option.stop_loss else option.stop_loss, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    elif curr_day_data.low <= option.target:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.open if curr_day_data.open < option.target else option.target, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting
                    if option is not None and curr_date.weekday() >= 4:
                        add_trade(trades, permno, symbol, curr_date, option, curr_day_data.close, -1, order.bar_vol, order.bar_type)
                        order, option = None, None
                        trading_state = TradingState.Hunting

            # We're waiting for an order to be executed:
            elif trading_state == TradingState.PendingOrder:
                if stock[curr_date] is None:
                    continue
                if (curr_date - order.date).days <= 4:
                    if curr_day_data.open <= order.call < curr_day_data.high:
                        option = Option(curr_date, "call", order.call, order.call + (order.call - order.call_stop_loss) * 2, order.call_stop_loss)
                        trading_state = TradingState.InPortfolio
                    elif curr_day_data.open >= order.put > curr_day_data.low:
                        option = Option(curr_date, "put", order.put, order.put - (order.put_stop_loss - order.put) * 2, order.put_stop_loss)
                        trading_state = TradingState.InPortfolio
                else:
                    trading_state = TradingState.Hunting
                    order = None

            # We're hunting for the right conditions:
            if trading_state == TradingState.Hunting:
                # TODO: Average volume
                if curr_date.weekday() == 4:
                    curr_friday = curr_date
                    curr_monday = curr_friday - datetime.timedelta(days=4 + (7 * (num_of_weeks - 1)))
                    prev_friday = curr_monday - datetime.timedelta(days=3)
                    prev_monday = prev_friday - datetime.timedelta(days=4 + (7 * (num_of_weeks - 1)))

                    curr_bar = get_bar(stock, curr_monday, curr_friday, permno, num_of_weeks)
                    prev_bar = get_bar(stock, prev_monday, prev_friday, permno, num_of_weeks)
                    if curr_bar is None or prev_bar is None:
                        continue

                    inside_bar, outside_bar = is_inside_bar(curr_bar, prev_bar), is_outside_bar(curr_bar, prev_bar)
                    if inside_bar or outside_bar:
                        fibo_call = curr_bar.high - (curr_bar.high - curr_bar.low) * 0.618
                        fibo_put = curr_bar.low + (curr_bar.high - curr_bar.low) * 0.618
                        order = Order(curr_date, curr_bar.high, curr_bar.low, fibo_call, fibo_put, curr_bar.volume, "IB" if inside_bar else "OB")
                        trading_state = TradingState.PendingOrder

        counter += 1
        percent = round(len(stocks_permnos) / 100)
        if percent > 0 and counter % percent == 0:
            print("\rFinished {}% of stocks...".format(round(counter / percent)), end="")

    trades_df = pd.DataFrame(trades, columns=list(trades.keys()))
    trades_df = trades_df.sort_values(['Buy_Date', 'Permno']).reset_index(
        drop=True)  # sorts the trades by buy date
    trades_df.to_csv(f'Options Trades {num_of_weeks} weeks.csv', index=False, header=True)
    print("\nDone in {:.0f} seconds! Options Trades {} weeks.csv".format(perf_counter() - counter_start, num_of_weeks))

    print_stats(trades_df)


def add_trade(trades, permno, symbol, curr_date, option, sell_price, sign, bar_vol, bar_type):
    trades['Permno'].append(permno)
    trades['Symbol'].append(symbol)
    trades['Buy_Date'].append(option.buy_date)
    trades['Buy_Price'].append(option.buy_price)
    trades['Sell_Date'].append(curr_date)
    trades['Sell_Price'].append(sell_price)
    trade_return = sign * (sell_price - option.buy_price) / option.buy_price
    trades['Return_Ratio'].append(str(round(100 * trade_return, 2)) + '%')
    trades['Bar_Volume'].append(bar_vol)
    trades['Bar_Type'].append(bar_type)


if __name__ == '__main__':
    back_test_run()
