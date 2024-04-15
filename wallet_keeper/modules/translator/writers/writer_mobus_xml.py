from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from wallet_keeper.modules.utils.xml_util import get_namespace, get_value, get_attr, get_element
from wallet_keeper.modules.translator.writers.base import WriterBase
from wallet_keeper.modules.utils.collection import *
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from datetime import datetime
import pandas
import re
import os
import hashlib

class WriterMobusXMLBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = WriterMobusXML()
        return self._instance


class WriterMobusXML(WriterBase):
    format = "mobus-xml"

    def __init__(self):
        pass

    @staticmethod
    def _write_comments(tran: Transfer, elem: ET.Element) -> None:
        """
        Write comments into xml elements

        :param tran: transfer or transaction
        :param elem: xml element
        :return:
        """
        # Tags
        if len(tran.tags) > 0:
            e_tags = ET.SubElement(elem, "tags")
            for tag in tran.tags:
                ET.SubElement(e_tags, "tag").text = tag

        # Properties
        if len(tran.properties) > 0:
            e_props = ET.SubElement(elem, "properties")
            for prop, val in tran.properties.items():
                e_prop = ET.SubElement(e_props, "property")
                ET.SubElement(e_prop, "name").text = prop
                ET.SubElement(e_prop, "value").text = val

        # Comments
        if len(tran.comments) > 0:
            e_comm = ET.SubElement(elem, "comments")
            for comment in tran.comments:
                ET.SubElement(e_comm, "comment").text = comment

        pass

    @staticmethod
    def _write_transfer(tran: Transfer, elem: ET.Element) -> None:
        """
        Write transfer into xml elements

        :param tran: transfer
        :param elem: xml element
        :return:
        """
        # Account
        t = ET.SubElement(elem, "transfer")
        ET.SubElement(t, "account").text = tran.account

        # Amount
        a = ET.SubElement(t, "amount")
        ET.SubElement(a, "value").text = str(tran.amount.value)
        ET.SubElement(a, "currency").text = tran.amount.currency

        # Price
        p = ET.SubElement(t, "totalPrice")
        ET.SubElement(p, "value").text = str(tran.price.value)
        ET.SubElement(p, "currency").text = tran.price.currency

        # Comments
        WriterMobusXML._write_comments(tran, t)

        pass

    @staticmethod
    def _write(transactions: List[Transaction], rules: Dict[str, Dict], **kwargs) -> List[ET.Element]:
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: reader specific arguments
        :return: matched and unmatched transaction lines
        """
        roots = []

        # Start XML file
        e_root = ET.Element('mobusTransfer')

        # Add transactions
        e_trans = ET.SubElement(e_root, "transactions")

        for i, t in enumerate(transactions):
            e_tran = ET.SubElement(e_trans, "transaction")

            # Write UID
            uid = hashlib.new("md5")
            uid.update((t.trans_date.strftime("%Y%m%d%H%M%S") + str(i)).encode("utf-8"))
            e_tran.set("uid", uid.hexdigest())

            # Write dates
            ET.SubElement(e_tran, "transaction_date").text = t.trans_date.strftime("%Y-%m-%dT%H:%M:%S")
            ET.SubElement(e_tran, "booking_date").text = t.book_date.strftime("%Y-%m-%dT%H:%M:%S")

            # Write name
            ET.SubElement(e_tran, "name").text = t.name

            # Write comments
            WriterMobusXML._write_comments(t, e_tran)

            # Write transfer
            ET.SubElement(e_tran, "transfers")
            for entry in t.transfers:
                WriterMobusXML._write_transfer(entry, e_tran)

        return [e_root]

    def write(self, transactions: List[Transaction], rules: Dict[str, Dict], path: Path, prefix="", **kwargs) -> List[Path]:
        """
        Write processed data to a file

        :param transactions: transactions to write
        :param rules: rules to assign transactions to accounts
        :param path: path to write to
        :param kwargs: reader specific arguments
        :param prefix: tag to add to the generated file names
        :return: dictionary with data as lists
        """
        files = []

        roots = WriterMobusXML._write(transactions, rules)
        for r in roots:
            # Write the xml file
            nf = path / "{}mobus_xml.xml".format(prefix)
            tree = ET.ElementTree(r)
            ET.indent(tree, space="\t", level=0)
            tree.write(str(nf), encoding="utf-8")
            files.append(nf)

        return files
