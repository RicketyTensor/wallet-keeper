from modules.translator.readers.reader_sparkasse_camt52v8 import ReaderSparkasseCAMT52v8Builder, ReaderSparkasseCAMT52v8
from modules.translator.readers.reader_ledger import ReaderLedgerBuilder, ReaderLedger


class ReaderFactory:
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


factory = ReaderFactory()
factory.register_builder(ReaderSparkasseCAMT52v8.format, ReaderSparkasseCAMT52v8Builder())
factory.register_builder(ReaderLedger.format, ReaderLedgerBuilder())
