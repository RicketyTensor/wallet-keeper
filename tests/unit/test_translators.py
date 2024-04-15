import unittest
import os
from pathlib import Path
from wallet_keeper.modules.translator.factory_reader import factory as fr
from wallet_keeper.modules.translator.factory_writer import factory as fw
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedger
from wallet_keeper.modules.translator.readers.reader_camt52v8 import ReaderCAMT52v8
from wallet_keeper.modules.translator.readers.reader_mobus_xml import ReaderMobusXML
from wallet_keeper.modules.translator.writers.writer_mobus_xml import WriterMobusXML
from wallet_keeper.modules.translator.writers.writer_ledger import WriterLedger
from wallet_keeper.modules.utils.collection import *
import pickle
import json
import pandas
import filecmp
import shutil


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = False

    def test_ledger_to_mobusXML(self):
        prefix = "ledger_to_mobusXML-"
        reader = fr.create(ReaderLedger.format)
        writer = fw.create(WriterMobusXML.format)

        rules = {}

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("reference/input/ledger.ledger"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(test_files) < 1:
            raise ValueError("No test filed were found!")

        for file in test_files:
            data = reader.read(file)
            result = writer.write(data, rules, out_dir, prefix)

            test_file = result[0]
            ref_file = p / "reference" / "translators" / os.path.basename(test_file)
            if self.update:
                shutil.copyfile(test_file, ref_file)

            if not filecmp.cmp(test_file, ref_file):
                raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))

    def test_mobusXML_to_mobusXML(self):
        prefix = "mobusXML_to_mobusXML-"
        reader = fr.create(ReaderMobusXML.format)
        writer = fw.create(WriterMobusXML.format)

        rules = {}

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("reference/input/mobus_xml.xml"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(test_files) < 1:
            raise ValueError("No test filed were found!")

        for file in test_files:
            data = reader.read(file)
            result = writer.write(data, rules, out_dir, prefix)

            test_file = result[0]
            ref_file = p / "reference" / "translators" / os.path.basename(test_file)
            if self.update:
                shutil.copyfile(test_file, ref_file)

            if not filecmp.cmp(test_file, ref_file):
                raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))

    def test_camt52v8_to_ledger(self):
        prefix = "camt52v8_to_ledger-"
        reader = fr.create(ReaderCAMT52v8.format)
        writer = fw.create(WriterLedger.format)

        rules = {
            "ledger.ledger": {
                "Extra Dental Insurance": {
                    cs_rule: {cs_creditor: ".*Krakenversicherung.*"},
                    cs_from: "Assets:Checking",
                    cs_to: "Expenses:Insurance:Dental"
                },
                "Life Insurance": {
                    cs_rule: {cs_creditor: ".*Life Insurance.*"},
                    cs_from: "Assets:Checking",
                    cs_to: "Expenses:Insurance:Life"
                },
                "Rent": {
                    cs_rule: {cs_message: ".*Miete.*"},
                    cs_from: "Assets:Checking",
                    cs_to: "Expenses:Rent"
                }
            }
        }

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("reference/input/camt52v8.xml"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(list(test_files)) < 1:
            raise ValueError("No test filed were found!")

        for file in test_files:
            data = reader.read(file)
            result = writer.write(data, rules, out_dir, prefix)

            test_file = result[0]
            ref_file = p / "reference" / "translators" / os.path.basename(test_file)
            if self.update:
                shutil.copyfile(test_file, ref_file)

            if not filecmp.cmp(test_file, ref_file):
                raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))


if __name__ == '__main__':
    unittest.main()
