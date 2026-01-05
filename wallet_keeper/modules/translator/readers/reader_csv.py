from pathlib import Path
from typing import List, Dict
from wallet_keeper.modules.translator.readers.base import ParserBase
from wallet_keeper.utils.collection import *
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.modules.core.wallet import Wallet
import numpy
from datetime import datetime
from decimal import Decimal


class ReaderCSVBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = ReaderCSV()
        return self._instance


class ReaderCSV(ParserBase):
    format = "csv"

    def __init__(self):
        pass

    @staticmethod
    def _read(path: Path, rules=None, raw=True, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: file to translate
        :param rules: dictionary with rules for parsing
        :param raw: read data as is
        :param kwargs: reader specific arguments
        :return: list of transactions
        """
        lines = []
        with open(path, "r") as rf:
            lines = rf.readlines()

        hl = rules[cs_header]
        header = lines[hl-1]

        def get_value(line, value):
            if type(value) is int:
                return line[value-1]
            elif isinstance(value, str):
                return value
            else:
                return None

        # Transactions
        transactions = []
        for line in lines[hl:]:
            columns = line.split(rules[cs_delimiter])

            clist = []
            for col in columns:
                clist.append(col.replace('"',''))

            amount = get_value(clist, rules[cs_columns][cs_amount])
            amount = amount.replace(rules[cs_format][cs_number][cs_thousand],"")
            amount = amount.replace(rules[cs_format][cs_number][cs_decimal],".")
            amount = float(amount)

            data = {
                cs_account: get_value(clist, rules[cs_columns][cs_account]),
                cs_institution: get_value(clist, rules[cs_columns][cs_institution]),
                cs_status: get_value(clist, rules[cs_columns][cs_status]),
                cs_valdate: get_value(clist, rules[cs_columns][cs_valdate]),
                cs_addinfo: get_value(clist, rules[cs_columns][cs_addinfo]),
                cs_creditor_name: get_value(clist, rules[cs_columns][cs_creditor_name]),
                cs_creditor_account: get_value(clist, rules[cs_columns][cs_creditor_account]),
                cs_debtor_name: get_value(clist, rules[cs_columns][cs_debtor_name]),
                cs_debtor_account: get_value(clist, rules[cs_columns][cs_debtor_account]),
                cs_amount: amount,
                cs_currency: get_value(clist, rules[cs_columns][cs_currency]),
                cs_message: get_value(clist, rules[cs_columns][cs_message])
            }

            valdate = datetime.strptime(get_value(clist, rules[cs_columns][cs_valdate]),rules[cs_format][cs_date])

            transactions.append(
                Transaction(
                    valdate, valdate, "Raw",
                    [], data, [],
                    [], raw=raw
                )
            )

        return transactions

    @staticmethod
    def read(paths: List[Path], rules: Dict = None, raw=True, **kwargs) -> Wallet:
        """
        Translate input to an output

        :param paths: list of files to translate
        :param rules: dictionary with rules for parsing
        :param raw: read data as is
        :param kwargs: reader specific arguments
        :return: wallet instance
        """
        transactions = []
        for path in paths:
            transactions.extend(ReaderCSV._read(path, rules, raw, **kwargs))

        return Wallet(transactions)
