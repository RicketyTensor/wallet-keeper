from wallet_keeper.modules.translator.readers.reader_camt52v8 import ReaderCAMT52v8
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedger
from wallet_keeper.modules.translator.writers.writer_ledger import WriterLedger

# Dictionary with allowed translations
# Key: Reader
# Value: Writer
allowed_translations = {
    ReaderCAMT52v8.format: WriterLedger.format,
    ReaderLedger.format: WriterLedger.format,
}
