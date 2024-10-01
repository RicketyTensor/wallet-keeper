from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from wallet_keeper.utils.xml_util import get_namespace, get_value, get_attr, get_element
from wallet_keeper.modules.translator.readers.base import ParserBase
from wallet_keeper.utils.collection import *
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.modules.core.wallet import Wallet
import numpy
from datetime import datetime
from decimal import Decimal

class ReaderCAMT52v8Builder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = ReaderCAMT52v8()
        return self._instance


class ReaderCAMT52v8(ParserBase):
    format = "camt52v8"

    def __init__(self):
        pass

    @staticmethod
    def _read(path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: reader specific arguments
        :return: list of transactions
        """
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {"ns": get_namespace(root)}

        # Account information
        acct = get_element(root, "ns:BkToCstmrAcctRpt/ns:Rpt/ns:Acct", ns)
        account = get_value(acct, "ns:Id/ns:IBAN", ns)
        institution = get_value(acct, "ns:Svcr/ns:FinInstnId/ns:Nm", ns)

        # Transactions
        transactions = []
        for entry in root.findall("ns:BkToCstmrAcctRpt/ns:Rpt/ns:Ntry", ns):
            details = get_element(entry, "ns:NtryDtls/ns:TxDtls", ns)

            # Basic
            status = get_value(entry, "ns:Sts/ns:Cd", ns)
            valdate = datetime.strptime(get_value(entry, "ns:ValDt/ns:Dt", ns), "%Y-%m-%d")
            addinfo = get_value(entry, "ns:AddtlNtryInf", ns)

            # Parties
            parties = get_element(details, "ns:RltdPties", ns)
            creditor_name = get_value(parties, "ns:Cdtr/ns:Pty/ns:Nm", ns, empty=True)
            creditor_acct = get_value(parties, "ns:CdtrAcct/ns:Id/ns:IBAN", ns, empty=True)
            debtor_name = get_value(parties, "ns:Dbtr/ns:Pty/ns:Nm", ns, empty=True)
            debtor_acct = get_value(parties, "ns:DbtrAcct/ns:Id/ns:IBAN", ns, empty=True)

            # Amount
            amount = Decimal(get_value(details, "ns:Amt", ns))
            currency = get_attr(details, "ns:Amt", ns, "Ccy")

            # Message
            messages = get_element(details, "ns:RmtInf", ns).findall("ns:Ustrd", ns)
            msgs = []
            for msg in messages:
                msgs.append(msg.text)
            message = " ".join(msgs)

            data = {
                cs_account: account,
                cs_institution: institution,
                cs_status: status,
                cs_valdate: valdate,
                cs_addinfo: addinfo,
                cs_creditor_name: creditor_name,
                cs_creditor_account: creditor_acct,
                cs_debtor_name: debtor_name,
                cs_debtor_account: debtor_acct,
                cs_amount: amount,
                cs_currency: currency,
                cs_message: message
            }

            transactions.append(
                Transaction(
                    valdate, valdate, "Raw",
                    [], data, [],
                    [], raw=True
                )
            )

        return transactions

    @staticmethod
    def read(path: Path, **kwargs) -> Wallet:
        """
        Translate input to an output

        :param path: list of files to translate
        :param kwargs: reader specific arguments
        :return: wallet instance
        """
        transactions = ReaderCAMT52v8._read(path, **kwargs)

        return Wallet(transactions)
