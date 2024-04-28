from typing import List, Dict
from wallet_keeper.modules.translator.readers.base import ParserBase
from wallet_keeper.modules.utils.collection import *
import re
from pathlib import Path
from datetime import datetime
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh


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

        :param line: line to process
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

    @staticmethod
    def _extract_transfer(line, i, path):
        """
        Extract transfer information from a line

        :param line: line to process
        :param i: line index number
        :param path: file path
        :return: account, amount, price, labels, tags, comments
        """
        # Check for labels, tags and comments
        l, t, c = ReaderLedger._extract_comments(line)

        if l or t or c:
            entry = line.split(";")[0]
        else:
            entry = line

        # Process actual values
        account = entry.split("  ")[0]
        fields = list(filter(None, entry.replace(account, "").split(" ")))

        # Deal with prices
        if len(fields) == 0:
            amount = None
            price = None
        elif len(fields) == 2:
            amount = Dosh(fields[0], fields[1])
            price = Dosh(fields[0], fields[1])
        elif len(fields) == 5:
            amount = Dosh(fields[0], fields[1])
            if fields[2] == "@":
                price = Dosh(fields[0], fields[4]) * Dosh(fields[3], fields[4])
            elif fields[2] == "@@":
                price = Dosh(fields[3], fields[4])
            else:
                raise ValueError(
                    "Unknown price specification on the line {} of {}".format(i + 1, path))
        else:
            raise ValueError(
                "Unknown transfer definition detected on the line {} of {}".format(i+1, path))

        return account, amount, price, l, t, c

    def _read(self, path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: reader specific arguments
        :return: dictionary with information
        """
        with open(path, "r") as f:
            lines = f.readlines()

        # Define variables
        trans_date = None
        book_date = None
        name = None
        labels = []
        tags = {}
        comments = []
        transfers = []

        # Go over lines
        transactions = []
        opened = False
        for i, line in enumerate(lines):
            if line.startswith("include"):
                include_path = path.parent / line.split(" ")[1].strip()
                transactions.extend(self._read(include_path), **kwargs)
            else:
                # Check for a date
                pattern = "([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])"
                match = re.findall(pattern, line)
                if len(match) == 0 and not opened:  # skip initial lines of a file till a transaction is detected
                    continue

                # First line of a transaction
                # ---------------------------
                elif len(match) > 0:
                    # Check if a transaction is ready to be closed
                    if not opened:  # Start the first transaction
                        opened = True
                    else:  # Finish an existing transaction
                        transactions.append(
                            Transaction(trans_date, book_date, name,
                                        labels, tags, comments,
                                        transfers
                                        )
                        )

                        # Restart variables
                        trans_date = None
                        book_date = None
                        name = None
                        labels = []
                        tags = {}
                        comments = []
                        transfers = []

                    # Read dates
                    if len(match) == 1:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = trans_date
                    elif len(match) == 2:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = datetime.strptime(match[1], "%Y-%m-%d")
                    else:
                        raise ValueError("Unknown date definition detected on the line {} of {}".format(i, path))

                    name = line.split(" ")[1].strip()

                    continue  # skip to the next line

            # Check for transaction wide tags and comments
                if line.strip().startswith(";"):
                    l, t, c = ReaderLedger._extract_comments(line)
                    if len(l) > 0:
                        labels.extend(l)
                    if len(t) > 0:
                        tags.update(t)
                    if len(c) > 0:
                        comments.extend(c)
                else:
                    # Process actual transfers
                    entry = line.strip()
                    if entry:
                        account, amount, price, l, t, c = ReaderLedger._extract_transfer(entry,i, path)
                        transfers.append(Transfer(account, amount, price, l, t, c))

        else:
            if opened:
                # Close last open transaction
                transactions.append(
                    Transaction(trans_date, book_date, name,
                                labels, tags, comments,
                                transfers
                                )
                )

        return transactions

    def read(self, path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: list of files to translate

        :param kwargs: reader specific arguments
        :return: dictionary with data as lists
        """
        return self._read(path, **kwargs)
