import argparse
from core.generator.parsers.sparkasse_camt52v8 import ParserSparkasseCAMT52v8
from pathlib import Path
from typing import List, Dict
import os
from core.generator.parser_factory import factory as pf
from core.generator.writer_factory import factory as wf
from core.utils.collection import *
import json
import glob
import pandas


def translate(files: List[Path], file_format: str, rules: dict, output: Path = None) -> None:
    """
    Translate to ledger format

    :param files: files to parse and use for database generation
    :param file_format: parser to use for reading the files
    :param rules: dictionary with rules for a deterministic tagging
    :param output: path to an output file
    :return: path to a written database
    """
    parser = pf.create(file_format)
    data = []
    for file in files:
        # 1. Parse
        data.extend(parser.parse(Path(file)))

    # 2. Write
    writer = wf.create("Ledger")
    matched = writer.write(data, rules, output)

    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='prepare',
        description='Preprocess')
    parser.add_argument("pattern", help="Glob pattern to recognize files")
    parser.add_argument("-r", "--rules", dest="rules", required=False,
                        help="Path to a JSON files with account rules")
    parser.add_argument("-f", "--format", dest="format",
                        choices=[ParserSparkasseCAMT52v8.format],
                        default=ParserSparkasseCAMT52v8.format, help="Format of the input files")
    parser.add_argument("-o", "--output", dest="output",
                        default=os.getcwd(), help="Output folder to which to write the files")
    args = parser.parse_args()

    rules = {}
    if args.rules:
        with open(args.rules, 'r') as f:
            rules = json.load(f)

    translate(glob.glob(args.pattern), args.format, rules, Path(args.output))
