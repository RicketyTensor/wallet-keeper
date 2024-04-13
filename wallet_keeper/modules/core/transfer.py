from typing import List, Dict
from wallet_keeper.modules.core.dosh import Dosh


class Transfer(object):
    def __init__(self, account: str, amount: Dosh, price: Dosh = None,
                 labels: List[str] = None, tags: Dict[str, str] = None, comments: List[str] = None):
        """
        Constructor

        :param account: account name
        :param amount: amount transferred
        :param price: price paid
        :param labels: list with labels (#LABEL)
        :param tags: dictionary with tags and values
        :param comments: date on which the transaction has been booked
        """
        self.account = account
        self.amount = amount
        self.price = price
        self.labels = labels
        self.tags = tags
        self.comments = comments
