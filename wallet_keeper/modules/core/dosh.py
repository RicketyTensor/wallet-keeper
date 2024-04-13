import decimal


class Dosh(object):
    def __init__(self, value: str = "0.0", currency: str = None):
        self._value = decimal.Decimal(value)
        self._currency = currency

    @property
    def value(self):
        return self._value

    @property
    def currency(self):
        return self._currency

    def __hash__(self):
        return hash((self._value, self._currency))

    def __repr__(self):
        return "{} {}".format(self._value, self._currency)

    def __str__(self):
        return "{} {:,.2f}".format(self._value, self._currency)

    def __add__(self, other):
        if isinstance(other, Dosh):
            if other.currency != self._currency:
                raise ValueError(
                    "Cannot add two different currencies {} and {}".format(self.currency, other.currency))
        return self.__class__(str(self.value + other.value), self._currency)

    def __sub__(self, other):
        if isinstance(other, Dosh):
            if other.currency != self._currency:
                raise ValueError(
                    "Cannot subtract two different currencies {} and {}".format(self.currency, other.currency))
        return self.__class__(str(self.value - other.value), self._currency)

    def __mul__(self, other):
        if isinstance(other, Dosh):
            if other.currency != self._currency:
                raise ValueError(
                    "Cannot multiple two different currencies {} and {}".format(self.currency, other.currency))
        return self.__class__(str(self.value * other.value), self._currency)
