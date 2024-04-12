from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from modules.utils.xml_util import get_namespace, get_value, get_attr, get_element
from modules.translator.readers.base import ParserBase
from modules.utils.collection import *
import pandas
import re
from pathlib import Path
from datetime import datetime
from modules.core.transaction import Transaction


class ReaderLedgerBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = ReaderLedger()
        return self._instance


class ReaderLedger(ParserBase):
    format = "ledger"

    def __init__(self):
        pass

    @staticmethod
    def _extract_comments(line):
        """
        Extract comments, tags and labels from a line

        :param line: line to check
        :return:
        """
        labels = []
        tags = {}
        comments = []

        messages = line.split(";")[1:]
        if len(messages) > 0:
            for msg in messages:
                potential_tags = re.findall(r"\S*:\s", msg)
                n = len(potential_tags)
                for j, tag in enumerate(potential_tags):
                    if j == n - 1:
                        value = re.findall(potential_tags[j] + r"(.*)",
                                           msg)[0].strip()
                    else:
                        value = re.findall(potential_tags[j] + r"(.*)" + potential_tags[j + 1],
                                           msg)[0].strip()

                    name = tag.replace(":", "").strip()
                    tags[name] = value
                    msg = msg.replace(tag, "")
                    msg = msg.replace(value, "")

                if msg.strip():
                    comments.append(msg.strip())

            # todo: One day, add reading for labels (#LABEL)

        return labels, tags, comments

    def _read(self, path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: parser specific arguments
        :return: dictionary with information
        """
        with open(path, "r") as f:
            lines = f.readlines()

        # Define variables
        trans_date = None
        book_date = None
        labels = []
        tags = {}
        comments = []

        # Go over lines
        transactions = []
        opened = False
        for i, line in enumerate(lines):
            if line.startswith("include"):
                include_path = path.parent / line.split(" ")[1].strip()
                transactions.extend(self._read(include_path), **kwargs)
            else:
                # Check for a date
                pattern = ".*([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]).*"
                match = re.findall(pattern, line)
                if len(match) > 0:
                    if not opened:  # Close existing transaction
                        opened = True
                    else:
                        transactions.append(
                            Transaction(trans_date, book_date,
                                        labels, tags, comments
                                        )
                        )

                        # Restart variables
                        trans_date = None
                        book_date = None
                        labels = []
                        tags = {}
                        comments = []

                    # Read dates
                    if len(match) == 1:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = trans_date
                    elif len(match) == 2:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = datetime.strptime(match[1], "%Y-%m-%d")
                    else:
                        raise ValueError("Unknown date definition detected on the line {} of {}".format(i, path))

                # Check for tags and comments
                if line.strip().startswith(";"):
                    l, t, c = self._extract_comments(line)
                    if len(l) > 0:
                        labels.extend(l)
                    if len(t) > 0:
                        tags.update(t)
                    if len(c) > 0:
                        comments.extend(c)

        return transactions

    def read(self, path: Path, **kwargs) -> List[Dict]:
        """
        Translate input to an output

        :param path: list of files to translate

        :param kwargs: parser specific arguments
        :return: dictionary with data as lists
        """
        return self._read(path, **kwargs)
