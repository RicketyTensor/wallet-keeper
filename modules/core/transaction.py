from datetime import datetime
from typing import Dict, List


class Transaction(object):
    def __init__(self, trans_date: datetime, book_date: datetime,
                 labels: List[str], tags: Dict[str, str], comments: List[str]):
        """
        Constructor

        :param trans_date: date of initiating the transaction
        :param book_date: date on which the transaction has been booked
        :param tags: dictionary with tags and values
        :param comments: date on which the transaction has been booked
        """
        self.trans_date = trans_date
        self.book_date = book_date
        self.labels = labels
        self.tags = tags
        self.comments = comments
