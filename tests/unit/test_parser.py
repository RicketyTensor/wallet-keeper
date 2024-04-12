import unittest
import os
from pathlib import Path
from modules.translator.factory_reader import factory
import pickle
import json
import pandas

class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = False

    def test_sparkasse_camt8(self):
        form = "camt52v8"
        parser = factory.create("Sparkasse CAMT52v8")
        p = Path(os.path.dirname(__file__))

        for file in p.glob("../input/{}/*.xml".format(form)):
            data = parser.read(file)
            ref_file = (os.path.splitext(os.path.basename(file))[0] + ".json")
            if self.update:
                with open(p / "reference" / form / ref_file, 'w') as f:
                    json.dump(data, f)
            with open(p / "reference" / form / ref_file, 'r') as f:
                ref = json.load(f)
            if not data == ref:
                raise AssertionError("Non matching results in {}!".format(os.path.basename(file)))


if __name__ == '__main__':
    unittest.main()
