import unittest
import os
from pathlib import Path

from wallet_keeper.modules.translator.factory_reader import factory as fr
from wallet_keeper.modules.translator.factory_writer import factory as fw
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedger
from wallet_keeper.modules.translator.readers.reader_camt52v8 import ReaderCAMT52v8
from wallet_keeper.modules.translator.readers.reader_csv import ReaderCSV
from wallet_keeper.modules.translator.writers.writer_ledger import WriterLedger
from wallet_keeper.modules.translator.writers.writer_gnucash import WriterGNUCash
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
            cs_transactions: {
                "Dental Insurance": {
                    cs_rule: {cs_creditor_name: ".*Krakenversicherung.*"},
                    cs_transfers: [
                        {
                            cs_account: "Assets:Checking"
                        },
                        {
                            cs_account: "Expenses:Insurance:Dental",
                            cs_props: {
                                cs_prop_provider: "Insurance ABC",
                                cs_prop_class: "Safety",
                                cs_prop_recurrence: "Monthly",
                            },
                            cs_labels: [
                                "Insurance"
                            ]
                        }
                    ],
                    cs_props: {
                        cs_prop_group: "special",
                    }
                },
                "Life Insurance": {
                    cs_rule: {
                        cs_creditor_name: ".*Life Insurance.*"
                    },
                    cs_props: {
                        cs_prop_group: "Special"
                    },
                    cs_transfers: [
                        {
                            cs_account: "Assets:Checking"
                        },
                        {
                            cs_account: "Expenses:Insurance:Life",
                            cs_props: {
                                cs_prop_id: "LV-1-2-3",
                                cs_prop_class: "Safety",
                                cs_prop_item: "Life Insurance",
                                cs_prop_provider: "Insurance ABC",
                                cs_prop_recurrence: "Monthly"
                            },
                            cs_labels: [
                                "Insurance"
                            ]
                        }
                    ]
                },
                "Rent": {
                    cs_rule: {
                        cs_message: ".*Miete.*"
                    },
                    cs_transfers: [
                        {
                            cs_account: "Assets:Checking"
                        },
                        {
                            cs_account: "Expenses:Rent",
                            cs_props: {
                                cs_prop_location: "Dumpster Nr. 9",
                                cs_prop_class: "Essential",
                                cs_prop_item: "Rent",
                                cs_prop_recurrence: "Monthly"
                            }
                        }
                    ],
                    cs_props: {
                        cs_prop_group: "Common"
                    }
                },
                "Groceries": {
                    cs_rule: {
                        cs_creditor_name: ".*Aldi.*"
                    },
                    cs_transfers: [
                        {
                            cs_account: "Assets:Checking"
                        },
                        {
                            cs_account: "Expenses:Groceries",
                            cs_props: {
                                cs_prop_class: "Essential",
                                cs_prop_item: "Groceries"
                            }
                        },
                        {
                            cs_account: "Expenses:Food:Groceries",
                            cs_props: {
                                cs_prop_class: "Essential",
                                cs_prop_item: "",
                                cs_prop_reason: "Lunch"
                            }
                        },
                        {
                            cs_account: "Expenses:Luxuries:Alcohol",
                            cs_props: {
                                cs_prop_class: "Entertainment",
                                cs_prop_item: ""
                            }
                        },
                        {
                            cs_account: "Expenses:Luxuries:Snacks",
                            cs_props: {
                                cs_prop_class: "Entertainment",
                                cs_prop_item: ""
                            }
                        }
                    ],
                    cs_props: {
                        cs_prop_shop: "EDEKA",
                        cs_prop_group: "Common"
                    }
                },
                "Buying Commodities": {
                    cs_rule: {
                        cs_addinfo: "WERTPAPIERE",
                        cs_message: ".*isin depp123456.*"
                    },
                    cs_transfers: [
                        {
                            cs_account: "Assets:Checking"
                        },
                        {
                            cs_account: "Equity:Securities:Fonds",
                            cs_props: {
                                cs_prop_broker: "Dealer",
                                cs_prop_class: "Finance",
                                cs_prop_item: "Buy",
                                cs_prop_fond: "Big Bollicks",
                                cs_prop_isin: "DEPP123456",
                                cs_prop_recurrence: "Monthly"
                            },
                            cs_commodity: {
                                cs_pattern: "ck *([0-9],[0-9][0-9][0-9][0-9])",
                                cs_name: "BALLS"
                            },
                            cs_price: {
                                cs_pattern: "preis *([0-9][0-9][0-9],[0-9][0-9][0-9][0-9])",
                                cs_name: "EUR"
                            },
                            cs_labels: [
                                "Investment",
                                "Finance",
                                "Stocks"
                            ]
                        }
                    ],
                    cs_props: {
                        cs_prop_group: "Special"
                    },
                    cs_fields: [
                        "creditor name"
                    ]
                },
            }
        }

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("input/camt52v8.xml"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(list(test_files)) < 1:
            raise ValueError("No test filed were found!")

        wallet = reader.read(test_files)
        wallet = process_wallet(wallet, rules[cs_transactions])
        results = writer.write(wallet, out_dir, prefix)

        for test_file in results:
            ref_file = p / "reference" / "translators" / os.path.basename(test_file)
            if self.update:
                shutil.copyfile(test_file, ref_file)

            if not filecmp.cmp(test_file, ref_file):
                raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))

    def test_csv_to_ledger(self):
        prefix = "csv_to_ledger-"
        reader = fr.create(ReaderCSV.format)
        writer = fw.create(WriterLedger.format)

        rules = {
            cs_delimiter: ";",
            cs_header: 5,
            cs_columns: {
                cs_account: 8,
                cs_institution: 10,
                cs_status: 3,
                cs_valdate: 2,
                cs_addinfo: None,
                cs_creditor_name: 5,
                cs_creditor_account: None,
                cs_debtor_name: 4,
                cs_debtor_account: None,
                cs_amount: 9,
                cs_currency: "EUR",
                cs_message: 6,
            },
            cs_format: {
                cs_number: {
                    cs_decimal: ",",
                    cs_thousand: "."
                },
                cs_date: "%d.%m.%y"
            },
            cs_transactions:
                {
                    "Salary": {
                        cs_rule: {
                            cs_message: ".*Lohn/Gehalt.*",
                            cs_debtor_name: ".*Employer.*"
                        },
                        cs_props: {
                            cs_prop_group: "Income",
                            cs_prop_recurrence: "Monthly"
                        },
                        cs_transfers: [
                            {
                                cs_account: "Income:Salary",
                                cs_props: {
                                    cs_prop_class: "Income",
                                    cs_prop_item: "Grundentgelt"
                                },
                                cs_labels: [
                                    "Income",
                                    "Salary"
                                ]
                            },
                            {
                                cs_account: "Expenses:Insurance:Pension",
                                cs_props: {
                                    cs_prop_class: "Safety",
                                    cs_prop_item: "Government Pension Insurance"
                                },
                                cs_labels: [
                                    "Government",
                                    "Insurance"
                                ]
                            },
                            {
                                cs_account: "Assets:Checking:Bank"
                            }
                        ]
                    },
                }
        }

        p = Path(os.path.dirname(__file__))
        test_files = list(p.glob("input/csv.csv"))
        out_dir = p / "output"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if len(list(test_files)) < 1:
            raise ValueError("No test filed were found!")

        wallet = reader.read(test_files, rules)
        wallet = process_wallet(wallet, rules[cs_transactions])
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

        wallet = reader.read(test_files)
        results = writer.write(wallet, out_dir, prefix)

        for test_file in results:
            ref_file = p / "reference" / "translators" / os.path.basename(test_file)
            if self.update:
                shutil.copyfile(test_file, ref_file)

            if not filecmp.cmp(test_file, ref_file):
                raise AssertionError("Test file {} doesn't match the reference {}!!".format(test_file, ref_file))


if __name__ == '__main__':
    unittest.main()
