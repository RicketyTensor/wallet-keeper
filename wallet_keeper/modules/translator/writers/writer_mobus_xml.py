from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from wallet_keeper.modules.translator.writers.base import WriterBase
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
import hashlib
from wallet_keeper.modules.translator.common.mobus_naming import *


class WriterMobusXMLBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = WriterMobusXML()
        return self._instance


class WriterMobusXML(WriterBase):
    format = cs_xml_root

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
            e_tags = ET.SubElement(elem, cs_tags)
            for tag in tran.tags:
                ET.SubElement(e_tags, cs_tag).text = tag

        # Properties
        if len(tran.properties) > 0:
            e_props = ET.SubElement(elem, cs_properties)
            for prop, val in tran.properties.items():
                e_prop = ET.SubElement(e_props, cs_property)
                ET.SubElement(e_prop, cs_name).text = prop
                ET.SubElement(e_prop, cs_value).text = val

        # Comments
        if len(tran.comments) > 0:
            e_comm = ET.SubElement(elem, cs_comments)
            for comment in tran.comments:
                ET.SubElement(e_comm, cs_comment).text = comment

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
        t = ET.SubElement(elem, cs_transfer)
        ET.SubElement(t, cs_account).text = tran.account

        # Amount
        a = ET.SubElement(t, cs_amount)
        ET.SubElement(a, cs_value).text = str(tran.amount.value)
        ET.SubElement(a, cs_currency).text = tran.amount.currency

        # Price
        p = ET.SubElement(t, cs_total_price)
        ET.SubElement(p, cs_value).text = str(tran.price.value)
        ET.SubElement(p, cs_currency).text = tran.price.currency

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
        e_root = ET.Element(cs_xml_root)

        # Go over transactions
        e_trans = ET.SubElement(e_root, cs_transactions)
        for i, t in enumerate(transactions):
            e_tran = ET.SubElement(e_trans, cs_transaction)

            # Write UID
            uid = hashlib.new("md5")
            uid.update((t.trans_date.strftime(datetime_format) + str(i)).encode("utf-8"))
            e_tran.set("uid", uid.hexdigest())

            # Write dates
            ET.SubElement(e_tran, cs_transaction_date).text = t.trans_date.strftime(datetime_format)
            ET.SubElement(e_tran, cs_booking_date).text = t.book_date.strftime(datetime_format)

            # Write name
            ET.SubElement(e_tran, cs_name).text = t.name

            # Write comments
            WriterMobusXML._write_comments(t, e_tran)

            # Write transfer
            e_transfers = ET.SubElement(e_tran, cs_transfers)
            for entry in t.transfers:
                WriterMobusXML._write_transfer(entry, e_transfers)

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
