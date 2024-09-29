import unittest
import os
from pathlib import Path
from wallet_keeper.modules.translator.factory_reader import factory
from wallet_keeper.modules.translator.readers.reader_mobus_xml import ReaderMobusXML
from wallet_keeper.modules.core.wallet import Wallet
from decimal import Decimal


class TestWallet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = False
        base = Path(os.path.dirname(__file__))
        file = base / "reference" / "visualizer" / "mobus_xml.xml"
        reader = factory.create(ReaderMobusXML.format)
        data = reader.read(Path(file))
        cls.wallet = Wallet()
        cls.wallet.build(data)
        pass

    def test_totals(self):
        df = self.wallet.get_pandas_totals()
        test = df.to_dict(orient="records")

        ref = [{'account': 'Assets:Checking', 'currency': 'EUR', 'amount': Decimal('-575.93')},
               {'account': 'Expenses:Alcohol', 'currency': 'EUR', 'amount': Decimal('21.0')},
               {'account': 'Expenses:Groceries', 'currency': 'EUR', 'amount': Decimal('31.6')},
               {'account': 'Expenses:Insurance:Life', 'currency': 'EUR', 'amount': Decimal('190.0')},
               {'account': 'Expenses:Rent', 'currency': 'EUR', 'amount': Decimal('333.33')}]

        if test != ref:
            raise ValueError("Non matching results!")

        pass


if __name__ == '__main__':
    unittest.main()
