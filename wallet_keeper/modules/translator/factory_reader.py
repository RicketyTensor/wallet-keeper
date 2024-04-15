from wallet_keeper.modules.translator.readers.reader_camt52v8 import ReaderCAMT52v8Builder, ReaderCAMT52v8
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedgerBuilder, ReaderLedger
from wallet_keeper.modules.translator.readers.reader_mobus_xml import ReaderMobusXMLBuilder, ReaderMobusXML


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
factory.register_builder(ReaderCAMT52v8.format, ReaderCAMT52v8Builder())
factory.register_builder(ReaderLedger.format, ReaderLedgerBuilder())
factory.register_builder(ReaderMobusXML.format, ReaderMobusXMLBuilder())
