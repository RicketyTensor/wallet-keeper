from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from wallet_keeper.utils.xml_util import get_namespace, get_value, get_element
from wallet_keeper.modules.translator.readers.base import ParserBase
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.modules.translator.common.mobus_naming import *
from datetime import datetime


class ReaderMobusXMLBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = ReaderMobusXML()
        return self._instance


class ReaderMobusXML(ParserBase):
    format = cs_xml_root

    def __init__(self):
        pass

    def _build_transfers(self, elem: ET.Element, ns: Dict[str, str]) -> List[Transfer]:
        """
        Get information from xml

        :param elem: xml element
        :param ns: dictionary of namespaces that are used in the address
        :return:
        """
        transfers = []
        e_trans = get_element(elem, "ns:{}".format(cs_transfers), ns)
        for e_tran in e_trans.findall("ns:{}".format(cs_transfer), ns):
            account = get_value(e_tran, "ns:{}".format(cs_account), ns)
            amount = Dosh(get_value(e_tran, "ns:{}/ns:{}".format(cs_amount, cs_value), ns),
                          get_value(e_tran, "ns:{}/ns:{}".format(cs_amount, cs_currency), ns))
            price = Dosh(get_value(e_tran, "ns:{}/ns:{}".format(cs_total_price, cs_value), ns),
                         get_value(e_tran, "ns:{}/ns:{}".format(cs_total_price, cs_currency), ns))

            # Tagging and co.
            tags = self._build_tags(e_tran, ns)
            properties = self._build_properties(e_tran, ns)
            comments = self._build_comments(e_tran, ns)

            transfers.append(Transfer(account, amount, price,
                                      tags, properties, comments))

        return transfers

    def _build_tags(self, elem: ET.Element, ns: Dict[str, str]) -> List[str]:
        """
        Get information from xml

        :param elem: xml element
        :param ns: dictionary of namespaces that are used in the address
        :return:
        """
        tags = []
        e_tags = get_element(elem, "ns:{}".format(cs_tags), ns, empty=True)
        if e_tags:
            for e_tag in e_tags.findall("ns:{}".format(cs_tag), ns):
                tags.append(e_tag.text)

        return tags

    def _build_properties(self, elem: ET.Element, ns: Dict[str, str]) -> Dict[str, str]:
        """
        Get information from xml

        :param elem: xml element
        :param ns: dictionary of namespaces that are used in the address
        :return:
        """
        properties = {}
        e_props = get_element(elem, "ns:{}".format(cs_properties), ns, empty=True)
        if e_props:
            for e_prop in e_props.findall("ns:{}".format(cs_property), ns):
                properties.update({
                    get_value(e_prop, "ns:{}".format(cs_name), ns): get_value(e_prop, "ns:{}".format(cs_value), ns)
                })

        return properties

    def _build_comments(self, elem: ET.Element, ns: Dict[str, str]) -> List[str]:
        """
        Get information from xml

        :param elem: xml element
        :param ns: dictionary of namespaces that are used in the address
        :return:
        """
        comments = []
        e_comments = get_element(elem, "ns:{}".format(cs_comments), ns, empty=True)
        if e_comments:
            for e_comm in e_comments.findall("ns:{}".format(cs_comment), ns):
                comments.append(e_comm.text)

        return comments

    def _build_transaction(self, elem: ET.Element, ns: Dict[str, str]) -> Transaction:
        """
        Build a transaction from an xml element

        :param elem: xml element
        :param ns: dictionary of namespaces that are used in the address
        :return:
        """

        # Basic
        trans_date = datetime.strptime(get_value(elem, "ns:{}".format(cs_transaction_date), ns), "%Y-%m-%dT%H:%M:%S")
        book_date = datetime.strptime(get_value(elem, "ns:{}".format(cs_booking_date), ns), "%Y-%m-%dT%H:%M:%S")
        name = get_value(elem, "ns:{}".format(cs_name), ns)

        # Tagging and co.
        tags = self._build_tags(elem, ns)
        properties = self._build_properties(elem, ns)
        comments = self._build_comments(elem, ns)

        # Add transfers
        transfers = self._build_transfers(elem, ns)

        return Transaction(trans_date, book_date, name, tags, properties, comments, transfers)

    def _read(self, path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: reader specific arguments
        :return: dictionary with information
        """
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {"ns": get_namespace(root)}

        # Loop over transactions
        transactions = []
        e_transactions = get_element(root, "ns:transactions", ns)
        for e_tran in e_transactions.findall("ns:transaction", ns):
            transactions.append(self._build_transaction(e_tran, ns))

        return transactions

    def read(self, path: Path, **kwargs) -> List[Transaction]:
        """
        Translate input to an output

        :param path: list of files to translate

        :param kwargs: reader specific arguments
        :return: dictionary with data as lists
        """
        return self._read(path, **kwargs)
