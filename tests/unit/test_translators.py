import unittest
import os
from pathlib import Path

from wallet_keeper.modules.translator.factory_reader import factory as fr
from wallet_keeper.modules.translator.factory_writer import factory as fw
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedger
from wallet_keeper.modules.translator.readers.reader_camt52v8 import ReaderCAMT52v8
from wallet_keeper.modules.translator.writers.writer_ledger import WriterLedger
from wallet_keeper.utils.collection import *
from wallet_keeper.modules.translator.processing import process_wallet
import filecmp
import shutil


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = False

    def test_camt52v8_to_ledger(self):
        prefix = "camt52v8_to_ledger-"
        reader = fr.create(ReaderCAMT52v8.format)
        writer = fw.create(WriterLedger.format)

        rules = {
            "Dental Insurance": {
                cs_rule: {cs_creditor_name: ".*Krakenversicherung.*"},
                cs_from: "Assets:Checking",
                cs_to: "Expenses:Insurance:Dental",
                cs_prop: {
                    cs_prop_group: "special",
                    cs_prop_class: "optional"
                }
            },
            "Life Insurance": {
                cs_rule: {cs_creditor_name: ".*Life Insurance.*"},
                cs_from: "Assets:Checking",
                cs_to: "Expenses:Insurance:Life",
                cs_prop: {
                    cs_prop_group: "special",
                    cs_prop_class: "optional"
                }
            },
            "Rent": {
                cs_rule: {cs_message: ".*Miete.*"},
                cs_from: "Assets:Checking",
                cs_to: "Expenses:Rent",
            },
            "Groceries": {
                cs_rule: {cs_creditor_name: "Aldi"},
                cs_from: "Assets:Checking",
                cs_to: [
                    "Expenses:Groceries",
                    "Expenses:Alcohol"
                ],
                cs_prop: {
                    cs_prop_group: "common",
                    cs_prop_shop: "Aldi"
                }
            },
            "Buying Commodities": {
                cs_rule: {
                    cs_addinfo: "WERTPAPIERE",
                    cs_message: ".*isin depp123456.*"
                },
                cs_from: "Assets:Checking",
                cs_to: "Equity:Securities:Fonds",
                cs_prop: {
                    cs_prop_fond: "Big Bollocks",
                    cs_prop_isin: "DEPP123456",
                    cs_prop_group: "special"
                },
                "commodity": {
                    "pattern": "ck *([0-9],[0-9][0-9][0-9][0-9])",
                    "name": "BALLS"
                },
                "price": {
                    "pattern": "preis *([0-9][0-9][0-9],[0-9][0-9][0-9][0-9])",
                    "name": "EUR"
                }
            }
        }

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("input/camt52v8.xml"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(list(test_files)) < 1:
            raise ValueError("No test filed were found!")

        for file in test_files:
            wallet = reader.read(file)
            wallet = process_wallet(wallet, rules)
            results = writer.write(wallet, out_dir, prefix)

            for test_file in results:
                ref_file = p / "reference" / "translators" / os.path.basename(test_file)
                if self.update:
                    shutil.copyfile(test_file, ref_file)

                if not filecmp.cmp(test_file, ref_file):
                    raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))

    def test_ledger_to_ledger(self):
        prefix = "ledger_to_ledger-"
        reader = fr.create(ReaderLedger.format)
        writer = fw.create(WriterLedger.format)

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("input/ledger.ledger"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(list(test_files)) < 1:
            raise ValueError("No test filed were found!")

        for file in test_files:
            wallet = reader.read(file)
            results = writer.write(wallet, out_dir, prefix)

            for test_file in results:
                ref_file = p / "reference" / "translators" / os.path.basename(test_file)
                if self.update:
                    shutil.copyfile(test_file, ref_file)

                if not filecmp.cmp(test_file, ref_file):
                    raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))

if __name__ == '__main__':
    unittest.main()
