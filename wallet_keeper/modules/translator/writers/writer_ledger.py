from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
from wallet_keeper.modules.utils.xml_util import get_namespace, get_value, get_attr, get_element
from wallet_keeper.modules.translator.writers.base import WriterBase
from wallet_keeper.modules.utils.collection import *
from datetime import datetime
import pandas
import re
import os


class WriterLedgerBuilder(object):
    def __init__(self):
        self._instance = None

    def __call__(self, **_ignored):
        if not self._instance:
            self._instance = WriterLedger()
        return self._instance


class WriterLedger(WriterBase):
    format = "ledger"

    def __init__(self):
        pass

    def _check_match(self, data: Dict, rule: Dict) -> bool:
        """
        Check if a rule is a match

        :param data: transaction data
        :param rule: rule to check for
        :return: True or False
        """
        check = True
        for k, r in rule.items():
            value = data[k]
            if value is not None:
                try:
                    pattern = re.compile(r)
                except re.error:
                    raise ValueError("Failed parsing regex pattern {}".format(r))
                check &= bool(pattern.match(value))
            else:
                check = False
                break

        return check

    def _make_entry(self, data: Dict, name: str, rule: Dict) -> List[str]:
        """
        Make a ledger entry

        :param data: transaction data
        :param name: name for the transaction
        :param rule: rule to apply
        :return: lines to write
        """
        lines = []

        # Process data
        date = data[cs_valdate]
        value = abs(data[cs_amount])
        currency = data[cs_currency]
        message = data[cs_message]
        commodity_amount = None
        commodity_name = None
        price_value = None
        price_currency = None

        if cs_commodity in rule.keys():
            pattern = rule[cs_commodity][cs_pattern]
            matches = re.findall(pattern, message.lower())
            if len(matches) < 1:
                pass
            else:
                match = matches[0].strip().replace(",", ".")
                commodity_amount = float(match)
                commodity_name = rule[cs_commodity][cs_name]

                pattern = rule[cs_price][cs_pattern]
                matches = re.findall(pattern, message.lower())
                match = matches[0].strip().replace(",", ".")
                price_value = float(match)
                price_currency = rule[cs_price][cs_name]

        # Detect extra dates in messages
        patterns = {
            ".*([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]).*": "%Y-%m-%d",
            ".*([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9]).*": "%d.%m.%Y"
        }
        actual_date = None
        for p, f in patterns.items():
            matches = re.findall(p, message)
            if len(matches) > 0:
                d = datetime.strptime(matches[0], f)
                actual_date = d.strftime("%Y-%m-%d")
                break

        # Write initial line
        if actual_date:
            lines.append("{}={} {}\n".format(actual_date, date, name))
        else:
            lines.append("{} {}\n".format(date, name))

        # Add tags
        if cs_tag in rule.keys():
            tags = rule[cs_tag]
            if type(tags) is str:
                tags = [tags]
            for tag in tags:
                lines.append("{:4}{} {}\n".format("", ";", tag))

        # Add requested fields
        if cs_fields in rule.keys():
            fields = rule[cs_fields]
            for f in fields:
                tag = f.capitalize()
                text = str(data[f]).capitalize()
                lines.append("{:4}{} {}\n".format("", ";", "{}: {}".format(tag, text)))

        # Write FROM account
        lines.append("{:4}{:50}\n".format("", rule[cs_from]))

        # Add TO account
        if commodity_amount:
            lines.append(
                "{:4}{:50}{:10.4f} {} @ {:.4f} {}\n".format("", rule[cs_to], commodity_amount, commodity_name,
                                                            price_value, price_currency))
        else:
            lines.append("{:4}{:50}{:10} {}\n".format("", rule[cs_to], value, currency))
        lines.append("\n")  # add an empty line

        return lines

    def _write(self, data: List[Dict], rules: Dict[str, Dict], **kwargs) -> (List, List):
        """
        Translate input to an output

        :param path: file to translate
        :param output_file: file into which to write
        :param kwargs: reader specific arguments
        :return: matched and unmatched transaction lines
        """
        # Sort transactions
        sorter = [(trans[cs_valdate], i) for i, trans in enumerate(data)]
        sorter.sort(key=lambda x: x[0])
        idx = lambda x: sorter[i][1]

        # Assign rules
        matcher = [""] * len(data)
        for name, rule in rules.items():
            match = False
            for i, transaction in enumerate(sorter):
                if len(matcher[i]) == 0:
                    r = rule[cs_rule]

                    if isinstance(r, dict):
                        match = self._check_match(data[idx(i)], r)
                    elif isinstance(r, list):
                        for ri in r:
                            match = self._check_match(data[idx(i)], ri)
                            if match:
                                break
                    else:
                        raise ValueError("Rule definition {} not supported.".format(name))

                    if match:
                        matcher[i] = name

        # Process rules and write
        matched = []
        unmatched = []
        for i, transaction in enumerate(sorter):
            if len(matcher[i]) > 0:
                matched.extend(self._make_entry(data[idx(i)], matcher[i], rules[matcher[i]]))
            else:
                unmatched.append(data[idx(i)])

        return matched, unmatched

    def write(self, data: List[Dict], rules: Dict[str, Dict], path: Path, prefix: str = "", **kwargs) -> List[str]:
        """
        Write processed data to a file

        :param data: data to write
        :param rules: rules to assign transactions to accounts
        :param path: path to write to
        :param prefix: tag to add to the generated file names
        :param kwargs: reader specific arguments
        :return: dictionary with data as lists
        """
        files = []
        unmatched = data
        for key, rule in rules.items():
            matched, unmatched = self._write(unmatched, rule, **kwargs)

            # Write matched
            outfile = path / "{}{}".format(prefix, key)
            with open(outfile, "w") as of:
                of.writelines(matched)
            files.append(outfile)
            print("INFO: Transactions were written to {}".format(outfile))

        # Write unmatched
        if len(unmatched) > 0:
            outfile = path / "{}unmatched.ledger".format(prefix)
            with open(outfile, "w") as of:
                for i, d in enumerate(unmatched):
                    # Write in a ledger format for simpler manual work
                    # lines = ["{:25}:\t{}\n".format(k, v) for k, v in d.items()]
                    default_name = d[cs_addinfo]
                    default_rule = {
                        cs_rule: {
                            cs_creditor: ".*"
                        },
                        cs_from: "Assets:XYZ",
                        cs_to: "Expenses:XYZ",
                        cs_tag: ["Item: XYZ", "Shop: XYZ"],
                        cs_fields: [cs_creditor, cs_message]
                    }
                    lines = self._make_entry(d, default_name, default_rule)
                    of.writelines(lines)
            files.append(outfile)
            print("WARNING: Unmatched transactions were found and written to {}".format(outfile))

        return files
