from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import pandas


class ParserBase(object):
    @abstractmethod
    def read(self, files: List[Path], output_file: Path, **kwargs) -> dict:
        """
        Translate input to an output

        :param files: list of files to translate
        :param output_file: file into which to write
        :param kwargs: parser specific arguments
        :return: dictionary with data as lists
        """
        pass
