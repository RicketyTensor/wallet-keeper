import unittest
import os
from pathlib import Path
from wallet_keeper.modules.translator.factory_writer import factory
from wallet_keeper.modules.translator.
import pickle
import pandas
from wallet_keeper.modules.utils.collection import *
from wallet_keeper.modules.utils.testing import assert_equal
import json
import filecmp
import shutil


class TestWriter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = False
        cls.rules = {
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

        pass

    def test_writer_camt_to_ledger(self):
        base = Path(os.path.dirname(__file__))
        file = base / "reference" / "input" / "ledger.json"

        # Read file with data and transform to pandas DataFrame
        with open(file, 'r') as f:
            data = json.load(f)

        writer = factory.create("Ledger")
        files = writer.write(data, self.rules, Path("."))

        # Check results
        for f in files:
            ref_file = base / "reference" / "ledger" / f
            if self.update:
                shutil.copyfile(f, ref_file)
            check = filecmp.cmp(f, ref_file, False)
            if not check:
                raise ValueError("The file of matched transactions is not identical to the reference!")

        pass


if __name__ == '__main__':
    unittest.main()
