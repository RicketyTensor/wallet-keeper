from typing import List, Dict
from wallet_keeper.modules.core.dosh import Dosh


class Transfer(object):
    def __init__(self, account: str, amount: Dosh = None, price: Dosh = None,
                 labels: List[str] = None, properties: Dict[str, str] = None, comments: List[str] = None):
        """
        Constructor

        :param account: account name
        :param amount: amount transferred
        :param price: price paid (total amount)
        :param labels: list with labels (#LABEL)
        :param properties: dictionary with tags and values
        :param comments: list of comments
        """
        self.account = account
        self.amount = amount
        self.price = price
        self.labels = labels
        self.properties = properties
        self.comments = comments
