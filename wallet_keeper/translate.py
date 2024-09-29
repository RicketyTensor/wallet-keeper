import argparse
from pathlib import Path
from typing import List
import os
from modules.translator.translations import allowed_translations
from modules.translator.factory_reader import factory as fr
from modules.translator.factory_writer import factory as fw
import json
import glob


def translate(files: List[Path], reader_format: str, writer_format: str, rules: dict, output: Path = None,
              tag: str = "") -> List[Path]:
    """
    Translate to ledger format

    :param files: files to parse and use for database generation
    :param reader_format: reader to use for reading the files
    :param writer_format: reader to use for writing the files
    :param rules: dictionary with rules for a deterministic tagging
    :param output: path to an output file
    :param tag: tag to add to the generated file names
    :return: path to a written database
    """
    reader = fr.create(reader_format)
    transactions = []
    for file in files:
        # 1. Parse
        transactions.extend(reader.read(Path(file)))

    # 2. Write
    writer = fw.create(writer_format)
    files = writer.write(transactions, rules, output, tag)

    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='prepare',
        description='Translate between various formats')
    parser.add_argument("pattern", help="Glob pattern to recognize files")
    parser.add_argument("-g", "--guide", dest="guide", required=False,
                        help="Path to a JSON files with account rules")
    parser.add_argument("-r", "--reader", dest="reader",
                        choices=allowed_translations.keys(),
                        default=list(allowed_translations.keys())[0].format,
                        help="Format of the input files")
    parser.add_argument("-w", "--writer", dest="writer",
                        choices=allowed_translations.values(),
                        default=list(allowed_translations.values())[0].format,
                        help="Format of the output files")
    parser.add_argument("-o", "--output", dest="output",
                        default=os.getcwd(),
                        help="Output folder to which to write the files")
    args = parser.parse_args()

    guide = {}
    if args.guide:
        with open(args.guide, 'r') as f:
            guide = json.load(f)

    files = translate(glob.glob(args.pattern), args.reader, args.writer, guide, Path(args.output))
