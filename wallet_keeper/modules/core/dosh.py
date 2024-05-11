import decimal


class Dosh(object):
    def __init__(self, value: str = "0.0", currency: str = None):
        try:
            self._value = decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise ValueError("Could not translate {} to a decimal format!".format(value))
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
            return self.__class__(str(self.value * other.value), self._currency)
        elif isinstance(other, int):
            return self.__class__(str(self.value * other), self._currency)
        elif isinstance(other, decimal.Decimal):
            return self.__class__(str(self.value * other), self._currency)
        elif isinstance(other, float):
            return self.__class__(str(self.value * decimal.Decimal(other)), self._currency)
        else:
            if other.currency != self._currency:
                raise ValueError(
                    "Cannot multiple two different currencies {} and {}".format(self.currency, other.currency))

