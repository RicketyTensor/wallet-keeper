from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict
import pandas


class WriterBase(object):
    @abstractmethod
    def write(self, data: List[Dict], rules: Dict[str, List[Dict]], path: Path, **kwargs) -> dict:
        """
        Write processed data to a file

        :param data: data to write
        :param rules: rules to assign transactions to accounts
        :param path: path to write to

        :param kwargs: reader specific arguments
        :return: dictionary with data as lists
        """
        pass
