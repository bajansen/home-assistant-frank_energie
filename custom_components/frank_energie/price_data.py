from datetime import datetime, timedelta

from homeassistant.util import dt


class Price:
    """ Price data for one hour"""

    date_from: datetime
    date_till: datetime
    market_price: float
    market_price_tax: float
    sourcing_markup_rice: float
    energy_tax_price: float

    def __init__(self, data: dict):
        self.date_from = dt.parse_datetime(data['from'])
        self.date_till = dt.parse_datetime(data['till'])

        self.market_price = data['marketPrice']
        self.market_price_tax = data['marketPriceTax']
        self.sourcing_markup_price = data['sourcingMarkupPrice']
        self.energy_tax_price = data['energyTaxPrice']

    @property
    def for_now(self):
        """ Whether this price entry is for the current hour. """
        return self.date_from <= dt.now() < self.date_till

    @property
    def for_future(self):
        """ Whether this price entry is for and hour after the current one. """
        return self.date_from.hour > dt.now().hour

    @property
    def for_today(self):
        """ Whether this price entry is for the current day. """
        day_start = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        return self.date_from >= day_start and self.date_till <= day_end

    @property
    def market_price_with_tax(self):
        return self.market_price + self.market_price_tax

    @property
    def total(self):
        return self.market_price + self.market_price_tax + self.sourcing_markup_price + self.energy_tax_price

    @property
    def hour(self):
        return self.date_from.astimezone()

class PriceData:

    def __init__(self, price_data: list[Price]):
        self.price_data = [Price(price) for price in price_data]

    @property
    def today(self) -> list[Price]:
        return [hour for hour in self.price_data if hour.for_today]

    @property
    def current_hour(self) -> Price:
        """ Price that's currently applicable. """
        return [hour for hour in self.price_data if hour.for_now][0]

    @property
    def today_min(self) -> Price:
        return min([hour for hour in self.today], key=lambda hour: hour.total)

    @property
    def today_max(self) -> Price:
        return max([hour for hour in self.today], key=lambda hour: hour.total)

    @property
    def today_avg(self) -> float:
        return round(sum(hour.total for hour in self.today) / len(self.today), 5)

    def get_future_prices(self):
        """ Prices for hours after the current one. """
        return [hour for hour in self.price_data if hour.for_future]
