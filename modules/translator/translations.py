from modules.translator.readers.reader_sparkasse_camt52v8 import ReaderSparkasseCAMT52v8
from modules.translator.readers.reader_ledger import ReaderLedger
from modules.translator.writers.writer_ledger import WriterLedger
from modules.translator.writers.writer_mobus import WriterMobus

# Dictionary with allowed translations
# Key: Reader
# Value: Writer
allowed_translations = {
    ReaderSparkasseCAMT52v8.format: WriterLedger.format,
    ReaderLedger.format: WriterMobus.format
}
