import decimal
from typing import List, Dict
from wallet_keeper.modules.translator.readers.base import ParserBase
import re
from pathlib import Path
from datetime import datetime
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.modules.core.wallet import Wallet
import numpy


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
    def _extract_comments(line) -> (List[str], Dict[str, str], List[str]):
        """
        Extract comments, tags and labels from a line

        :param line: line to process
        :return:
        """
        labels = []
        properties = {}
        comments = []

        messages = line.strip().split(";")[1:]
        if len(messages) > 0:
            for message in messages:
                msg = message

                # Check for labels
                potential_labels = ["".join(e) for e in re.findall(r"(?>:(\S))(.*?)(?=(\S):)", msg)]
                if len(potential_labels) > 0:
                    labels.extend(potential_labels)
                for label in potential_labels:
                    msg = msg.replace(label + ":", "")
                msg = msg.replace(" :","").strip()

                potential_tags = re.findall(r"(^[A-z].*\S:)", msg)
                n = len(potential_tags)
                for j, tag in enumerate(potential_tags):
                    if j == n - 1:
                        value = re.findall(potential_tags[j] + r"(.*)",
                                           msg)[0].strip()
                    else:
                        value = re.findall(potential_tags[j] + r"(.*)" + potential_tags[j + 1],
                                           msg)[0].strip()

                    name = tag.replace(":", "").strip()
                    properties[name] = value
                    msg = msg.replace(tag, "")
                    msg = msg.replace(value, "")

                if msg.strip():
                    comments.append(msg.strip())

        return labels, properties, comments

    @staticmethod
    def _extract_transfer(line, i, path) -> (str, Dosh, Dosh, List[str], Dict[str, str], List[str]):
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
            price = None
            #price = Dosh(fields[0], fields[1])
        elif len(fields) == 5:
            amount = Dosh(fields[0], fields[1])
            if fields[2] == "@":
                price = Dosh(numpy.abs(float(fields[0])), fields[4]) * Dosh(fields[3], fields[4])
            elif fields[2] == "@@":
                price = Dosh(fields[3], fields[4])
            else:
                raise ValueError("Unknown price specification on the line {} of {}".format(i + 1, path))
        else:
            raise ValueError("Unknown transfer definition detected on the line {} of {}".format(i + 1, path))

        return account, amount, price, l, t, c

    @staticmethod
    def _read(path: Path, raw=True, **kwargs) -> (List[Transaction], Dict[str, str], Transaction, Transaction):
        """
        Translate input to an output

        :param path: file to translate
        :param raw: read data as is
        :param kwargs: reader specific arguments
        :return: wallet instance
        """
        with open(path, "r") as f:
            lines = f.readlines()

        # Define variables
        account_labels = {}
        budget_monthly = None
        budget_yearly = None
        budg_factor = 1
        trans_date = None
        book_date = None
        name = None
        t_labels = []
        t_properties = {}
        t_comments = []
        tt_labels = []
        tt_properties = {}
        tt_comments = []
        transfers = []
        account = None
        amount = None
        price = None

        # Go over lines
        transactions = []
        transaction_open = False
        transfer_open = False
        budg_m_opened = False
        budg_y_opened = False
        for i, line in enumerate(lines):
            if line.startswith("include"):
                include_path = path.parent / line.split(" ")[1].strip()
                tr, al, bm, by = ReaderLedger._read(include_path, **kwargs)
                transactions.extend(tr)
                account_labels.update(al)
                budget_monthly = bm if bm else budget_monthly
                budget_yearly = by if by else budget_yearly
            elif line.startswith("account"):
                s = line.replace("account", "").strip()
                splits = s.split(";")
                acc = splits[0].strip()
                if len(splits) > 1:
                    cat = splits[-1].strip().replace("#", "")
                else:
                    cat = None
                account_labels.update({acc: cat})
            elif line.startswith("~ Monthly"):
                budg_m_opened = True
                budg_y_opened = False
            elif line.startswith("~ Yearly"):
                budg_m_opened = False
                budg_y_opened = True
            else:
                # Check for a date
                pattern = "([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])"
                match = re.findall(pattern, line)

                if len(match) == 0 and not (transaction_open or budg_m_opened or budg_y_opened):  # skip initial lines of a file till a transaction is detected
                    continue
                elif not line.strip():
                    if transaction_open:
                        if transfer_open:
                            transfers.append(Transfer(account, amount, price, tt_labels, tt_properties, tt_comments))
                            tt_labels = []
                            tt_properties = {}
                            tt_comments = []
                            transfer_open = False

                        transaction_open = False
                        transactions.append(
                            Transaction(
                                trans_date, book_date, name,
                                t_labels, t_properties, t_comments,
                                transfers, raw=raw
                            )
                        )
                    elif budg_m_opened:
                        budg_m_opened = False
                        budget_monthly = Transaction(
                            trans_date, book_date, name,
                            t_labels, t_properties, t_comments,
                            transfers, raw=raw
                        )
                    elif budg_y_opened:
                        budg_y_opened = False
                        budget_yearly = Transaction(
                            trans_date, book_date, name,
                            t_labels, t_properties, t_comments,
                            transfers, raw=raw
                        )

                    # Restart variables
                    trans_date = None
                    book_date = None
                    name = None
                    t_labels = []
                    t_properties = {}
                    t_comments = []
                    transfers = []

                # First line of a transaction
                # ---------------------------
                elif len(match) > 0:
                    budg_m_opened = False
                    budg_y_opened = False

                    # Check if a transaction is ready to be closed
                    if not transaction_open:  # Start the first transaction
                        transaction_open = True

                    # Read dates
                    if len(match) == 1:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = trans_date
                    elif len(match) == 2:
                        trans_date = datetime.strptime(match[0], "%Y-%m-%d")
                        book_date = datetime.strptime(match[1], "%Y-%m-%d")
                    else:
                        raise ValueError("Unknown date definition detected on the line {} of {}".format(i, path))

                    name = " ".join(line.strip().split(" ")[1:])

                    continue  # skip to the next line

                # Check for transaction wide tags and comments
                if line.strip().startswith(";"):
                    l, t, c = ReaderLedger._extract_comments(line)
                    if transfer_open:
                        if len(l) > 0:
                            tt_labels.extend(l)
                        if len(t) > 0:
                            tt_properties.update(t)
                        if len(c) > 0:
                            tt_comments.extend(c)
                    elif transaction_open:
                        if len(l) > 0:
                            t_labels.extend(l)
                        if len(t) > 0:
                            t_properties.update(t)
                        if len(c) > 0:
                            t_comments.extend(c)


                else:
                    # Process transfers
                    # -----------------
                    entry = line.strip()
                    if entry:
                        if transfer_open:
                            transfers.append(Transfer(account, amount, price, tt_labels, tt_properties, tt_comments))
                            tt_labels = []
                            tt_properties = {}
                            tt_comments = []
                        transfer_open = True

                        account, amount, price, l, t, c = ReaderLedger._extract_transfer(entry, i, path)
                        if len(l) > 0:
                            tt_labels.extend(l)
                        if len(t) > 0:
                            tt_properties.update(t)
                        if len(c) > 0:
                            tt_comments.extend(c)


        else:
            if transaction_open:
                if transfer_open:
                    transfers.append(Transfer(account, amount, price, tt_labels, tt_properties, tt_comments))
                    tt_labels = []
                    tt_properties = {}
                    tt_comments = []
                    transfer_open = False

                transactions.append(
                    Transaction(
                        trans_date, book_date, name,
                        t_labels, t_properties, t_comments,
                        transfers, raw=raw
                    )
                )
            elif budg_m_opened:
                budget_monthly = Transaction(
                    trans_date, book_date, name,
                    t_labels, t_properties, t_comments,
                    transfers, raw=raw
                )
            elif budg_y_opened:
                budget_yearly = Transaction(
                    trans_date, book_date, name,
                    t_labels, t_properties, t_comments,
                    transfers, raw=raw
                )

        return transactions, account_labels, budget_monthly, budget_yearly

    @staticmethod
    def read(path: Path, raw=True, **kwargs) -> Wallet:
        """
        Translate input to an output

        :param path: list of files to translate
        :param raw: read data as is
        :param kwargs: reader specific arguments
        :return: wallet instance
        """
        transactions, account_labels, budget_monthly, budget_yearly = ReaderLedger._read(path, raw, **kwargs)

        return Wallet(transactions, account_labels, budget_monthly, budget_yearly)
