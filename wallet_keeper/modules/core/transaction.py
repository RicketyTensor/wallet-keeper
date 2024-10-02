from datetime import datetime
from typing import Dict, List
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.modules.core.transfer import Transfer
import numpy


class Transaction(object):
    def __init__(self, trans_date: datetime, book_date: datetime, name: str,
                 labels: List[str], properties: Dict[str, str], comments: List[str],
                 transfers: List[Transfer], raw=False):
        """
        Constructor

        :param trans_date: date of initiating the transaction
        :param book_date: date on which the transaction has been booked
        :param name: name of the transaction
        :param labels: list with labels (#LABEL)
        :param properties: dictionary with tags and values
        :param comments: text comment
        :param transfers: changes to account states
        """
        self.trans_date = trans_date if trans_date else book_date
        self.book_date = book_date
        self.name = name
        self.labels = labels
        self.properties = properties
        self.comments = comments
        self.transfers = transfers

        if not raw:
            self._balance()

    def _balance(self):
        """
        Balance this transaction

        :return:
        """

        def date(x):
            return x.strftime("%Y-%m-%d")

        # Check if only one empty amount has been specified
        empty_transfers = [t for t in self.transfers if t.amount is None]
        if len(empty_transfers) > 1:
            raise ValueError("The following transaction cannot be balanced!\n"
                             "Reason: Only one transfer may remain empty!"
                             "{}={} {}".format(date(self.trans_date), date(self.book_date), self.name))
        transfers = list(filter(lambda t: t.amount is not None, self.transfers))

        # Check for different currencies
        currencies = list(set(t.price.currency for t in transfers))
        if len(currencies) > 1:
            raise ValueError("The following transaction cannot be balanced!\n"
                             "Reason: Various currencies cannot be currently automatically balanced!"
                             "{}={} {}".format(date(self.trans_date), date(self.book_date), self.name))

        # Compute totals
        currency = currencies[0]
        delta = Dosh("0.0", currency)
        for t in transfers:
            delta -= t.price

        if delta.value != 0.0 and len(empty_transfers) == 0:
            raise ValueError("The following transaction cannot be balanced!\n"
                             "Reason: Transaction is unbalanced and no account is free for balancing!\n"
                             "{}={} {}".format(date(self.trans_date), date(self.book_date), self.name))
        elif len(empty_transfers) == 1:
            t = empty_transfers[0]
            t.amount = delta
            t.price = delta
        elif len(empty_transfers) == 0:
            pass
        else:
            raise ValueError("The following transaction cannot be balanced!\n"
                             "Reason: Unknown failure condition!\n"
                             "{}={} {}".format(date(self.trans_date), date(self.book_date), self.name))
