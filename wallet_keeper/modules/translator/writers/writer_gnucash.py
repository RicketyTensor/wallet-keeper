from collections import defaultdict
from pathlib import Path
from typing import List, Dict
from wallet_keeper.modules.translator.writers.base import WriterBase
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from datetime import datetime
import re
from wallet_keeper.utils.collection import *


class WriterGNUCashBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = WriterGNUCash()
        return self._instance


class WriterGNUCash(WriterBase):
    format = "gnucash"

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

        if not transfer.amount:
            lines.append(
                "{:4}{:40}{:10} {} \n".format("", transfer.account, "", ""))
        elif abs(transfer.amount) == transfer.price:
            lines.append(
                "{:4}{:40}{:10.2f} {} \n".format("", transfer.account,
                                                 transfer.amount.value, transfer.amount.currency))
        elif transfer.price:
            lines.append(
                "{:4}{:40}{:10.4f} {} @@ {:.4f} {}\n".format("", transfer.account,
                                                             transfer.amount.value, transfer.amount.currency,
                                                             transfer.price.value, transfer.price.currency))
        else:
            raise ValueError("Un-allowed amount definition in a transfer {}".format(transfer.amount))

        # Add comments
        for comment in transfer.comments:
            lines.append("{:4}{} {}\n".format("", ";", comment))

        # Add tags/labels
        if len(transfer.labels) > 0:
            lines.append("{:4}{} :{}:\n".format("", ";", ":".join(transfer.labels)))

        # Add properties
        for name, prop in dict(sorted(transfer.properties.items())).items():
            lines.append("{:4}{} {}: {}\n".format("", ";", name, prop))

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

        # Add comments
        for comment in trans.comments:
            lines.append("{:4}{} {}\n".format("", ";", comment))

        # Add tags/labels
        if len(trans.labels) > 0:
            lines.append("{:4}{} :{}:\n".format("", ";", ":".join(trans.labels)))

        # Add properties
        for name, prop in dict(sorted(trans.properties.items())).items():
            lines.append("{:4}{} {}: {}\n".format("", ";", name, prop))

        # Add transfers
        for transfer in trans.transfers:
            lines.extend(WriterGNUCash._write_transfer(transfer))

        lines.append("\n")  # add an empty line

        return lines

    @staticmethod
    def _write_accounts(wallet) -> str:
        """
        Write lines for accounts

        :param wallet: wallet with data
        :return: list of files written
        """
        lines = []

        # Header
        header = ["Type",
                  "Account Full Name",
                  "Account Name",
                  "Account Code",
                  "Description",
                  "Account Colour",
                  "Notes",
                  "Symbol",
                  "Namespace",
                  "Hidden",
                  "Tax Info",
                  "Placeholder"
                  ]
        lines.append(",".join(header))

        # Contents
        accounts = wallet.get_list_accounts()
        for acc in accounts:
            breakdown = acc.split(":")
            info = {
                "Type": breakdown[0],
                "Account Full Name": acc,
                "Account Name": breakdown[-1],
                "Account Code": "",
                "Description": "",
                "Account Colour": "",
                "Notes": "",
                "Symbol": "",
                "Namespace": "",
                "Hidden": "",
                "Tax Info": "",
                "Placeholder": ""
            }
            line_list = [info[k] for k in header]
            lines.append(",".join(line_list))

        return "\n".join(lines)

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
        group_by = cs_prop_group

        # Accounts

        lines = WriterGNUCash._write_accounts(wallet)
        files.update({"accounts": lines})

        # Transactions
        # dates = [t.book_date for t in wallet.transactions]
        # timed = [x for _, x in sorted(zip(dates, wallet.transactions),key=lambda x: x[0])]
        # for trans in timed:
        #     lines = WriterCSV._write_transaction(trans)
        #     group = trans.properties[group_by].lower() if group_by in trans.properties.keys() else "ungrouped"
        #     if group not in files.keys():
        #         files.update({group: lines})
        #     else:
        #         files[group].extend(lines)

        return files

    @staticmethod
    def write(wallet, path: Path, prefix: str = "", suffix: str = "", **kwargs) -> List[str]:
        """
        Write processed data to a file

        :param wallet: wallet with data
        :param path: path to the directory to write to
        :param prefix: tag to add to the generated file names
        :param suffix: tag to add to the end of the generated file names
        :param kwargs: reader specific arguments
        :return: list of files written
        """
        files = WriterGNUCash._write(wallet, **kwargs)
        output = []
        for key, text in files.items():
            output.append(path / "{}{}{}".format(prefix, key, suffix))
            with open(output[-1], "w") as f:
                f.writelines(text)

        return output
