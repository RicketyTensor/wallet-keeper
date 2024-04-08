from core.generator.parsers.sparkasse_camt52v8 import ParserSparkasseCAMT52v8Builder, ParserSparkasseCAMT52v8

class ParserFactory:
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


factory = ParserFactory()
factory.register_builder(ParserSparkasseCAMT52v8.format, ParserSparkasseCAMT52v8Builder())
