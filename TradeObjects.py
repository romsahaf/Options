import datetime as datetime
from dataclasses import dataclass
import enum


class DayData:
    def __init__(self, date, openn, close, high, low, volume):
        self.date: datetime = datetime.date(*list(map(int, date.split('-'))))
        self.open: float = openn
        self.close: float = close
        self.high: float = high
        self.low: float = low
        self.volume: int = volume


@dataclass
class Bar:
    start_date: datetime
    open: float
    close: float
    high: float
    low: float
    volume: int


@dataclass
class Order:
    date: datetime
    call: float
    put: float
    call_stop_loss: float
    put_stop_loss: float
    bar_vol: float
    bar_type: str


@dataclass
class Option:
    buy_date: datetime
    type: str
    buy_price: float
    target: float
    stop_loss: float


class TradingState(enum.Enum):
    Hunting = 1
    PendingOrder = 2
    InPortfolio = 3
