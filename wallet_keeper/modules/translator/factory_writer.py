from wallet_keeper.modules.translator.writers.writer_ledger import WriterLedgerBuilder, WriterLedger
from wallet_keeper.modules.translator.writers.writer_mobus import WriterMobusBuilder, WriterMobus

class WriterFactory:
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


factory = WriterFactory()
factory.register_builder(WriterLedger.format, WriterLedgerBuilder())
factory.register_builder(WriterMobus.format, WriterMobusBuilder())
