from collections import defaultdict
from pathlib import Path
from typing import List, Dict
from wallet_keeper.modules.translator.writers.base import WriterBase
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from datetime import datetime
import re
from wallet_keeper.utils.collection import *


class WriterLedgerBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = WriterLedger()
        return self._instance


class WriterLedger(WriterBase):
    format = "ledger"

    def __init__(self):
        pass

    @staticmethod
    def _write_transfer(transfer: Transfer) -> List[str]:
        """
        Write a single transfer

        :param transfer: transfer
        :return: list of lines
        """
        lines = []

        if transfer.price:
            lines.append(
                "{:4}{:50}{:10.4f} {} @ {:.4f} {}\n".format("", transfer.account,
                                                            transfer.amount.value, transfer.amount.currency,
                                                            transfer.price.value, transfer.price.currency))
        elif transfer.amount:
            lines.append(
                "{:4}{:50}{:10.2f} {} \n".format("", transfer.account,
                                                 transfer.amount.value, transfer.amount.currency))
        else:
            lines.append(
                "{:4}{:50}{:10} {} \n".format("", transfer.account, "", ""))

        return lines

    @staticmethod
    def _write_transaction(trans: Transaction) -> List[str]:
        """
        Write lines of a single transaction

        :param trans: transaction
        :return: list of lines
        """
        lines = []

        # First line
        date2 = trans.book_date.strftime("%Y-%m-%d")
        if trans.trans_date:
            date1 = trans.trans_date.strftime("%Y-%m-%d")
            lines.append("{}={} {}\n".format(date1, date2, trans.name))
        else:
            lines.append("{} {}\n".format(date2, trans.name))

        # Add tags
        for tag in trans.tags:
            lines.append("{:4}{} {}\n".format("", ";", tag))

        # Add properties
        for name, prop in trans.properties.items():
            lines.append("{:4}{} {}: {}\n".format("", ";", name, prop))

        # Add comments
        for comment in trans.comments:
            lines.append("{:4}{} {}\n".format("", ";", comment))

        for transfer in trans.transfers:
            lines.extend(WriterLedger._write_transfer(transfer))

        lines.append("\n")  # add an empty line

        return lines

    @staticmethod
    def _write(wallet, **kwargs) -> Dict[str, List[str]]:
        """
        Write processed data to a file

        :param wallet: wallet with data
        :param path: path to the directory to write to
        :param prefix: tag to add to the generated file names
        :param kwargs: reader specific arguments
        :return: list of files written
        """
        files = defaultdict(list)
        group_by = cs_category
        for trans in wallet.transactions:
            lines = WriterLedger._write_transaction(trans)
            group = trans.properties[group_by].lower() if group_by in trans.properties.keys() else "ungrouped"
            if group not in files.keys():
                files.update({group: lines})
            else:
                files[group].extend(lines)

        return files

    @staticmethod
    def write(wallet, path: Path, prefix: str = "", **kwargs) -> List[str]:
        """
        Write processed data to a file

        :param wallet: wallet with data
        :param path: path to the directory to write to
        :param prefix: tag to add to the generated file names
        :param kwargs: reader specific arguments
        :return: list of files written
        """
        files = WriterLedger._write(wallet, **kwargs)
        output = []
        for key, text in files.items():
            output.append(path / "{}{}".format(prefix, key))
            with open(output[-1], "w") as f:
                f.writelines(text)

        return output
