from wallet_keeper.modules.core.wallet import Wallet
from wallet_keeper.modules.core.transaction import Transaction
from wallet_keeper.modules.core.transfer import Transfer
from wallet_keeper.modules.core.dosh import Dosh
from wallet_keeper.utils.collection import *
from typing import List, Dict
from datetime import datetime
import re

def _check_match(trans: Transaction, rule: Dict) -> bool:
    """
    Check if a rule is a match

    :param data: transaction
    :param rule: rule to check for
    :return: True or False
    """
    check = True
    for k, r in rule.items():
        value = trans.properties[k]
        if value is not None:
            try:
                pattern = re.compile(r.lower())
            except re.error:
                raise ValueError("Failed parsing regex pattern {}".format(r))
            check &= bool(pattern.match(value.lower()))
        else:
            check = False
            break

    return check


def _process_transaction(trans: Transaction, name: str, rule: Dict) -> None:
    """
    Make a processed ledger entry

    :param trans: transaction
    :param name: name for the transaction
    :param rule: rule to apply
    """
    lines = []

    # Process data
    message = trans.properties[cs_message]
    labels = []
    properties = {}
    comments = []
    transfers = []

    # Dates
    # =====
    patterns = {
        ".*([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]).*": "%Y-%m-%d",
        ".*([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9]).*": "%d.%m.%Y"
    }
    for p, f in patterns.items():
        matches = re.findall(p, message)
        if len(matches) > 0:
            actual_date = datetime.strptime(matches[0], f)
            break
    else:
        actual_date = None

    # Commodities
    # ===========
    amount = Dosh(trans.properties[cs_amount], trans.properties[cs_currency])
    price = None
    commodity = None
    if cs_commodity in rule.keys():
        pattern = rule[cs_commodity][cs_pattern]
        matches = re.findall(pattern, message.lower())
        if len(matches) < 1:
            pass
        else:
            match = matches[0].strip().replace(",", ".")
            commodity_amount = match
            commodity_name = rule[cs_commodity][cs_name]
            commodity = Dosh(commodity_amount, commodity_name)

            pattern = rule[cs_price][cs_pattern]
            matches = re.findall(pattern, message.lower())
            if len(matches) < 1:
                raise ValueError("Pattern \"{}\" was not detected in the text \"{}\"".format(pattern, message))
            match = matches[0].strip().replace(",", ".")
            price_value = match
            price_currency = rule[cs_price][cs_name]
            price = Dosh(price_value, price_currency) * Dosh(commodity_amount, price_currency)

    # Add tags
    if cs_tag in rule.keys():
        labels = rule[cs_tag]
    else:
        labels = []

    # Add properties
    if cs_prop in rule.keys():
        properties.update(rule[cs_prop])

    # Add requested fields
    if cs_fields in rule.keys():
        fields = rule[cs_fields]
        for f in fields:
            properties.update({f.capitalize(): str(trans.properties[f]).capitalize()})

    # FROM transfer
    # =============
    sign = -1 if trans.properties[cs_debtor_account] == trans.properties[cs_account] else 1
    transfers.append(
        Transfer(rule[cs_from], amount * sign, None)
    )

    # TO transfer
    # ===========
    if type(rule[cs_to]) != list:
        rule[cs_to] = [rule[cs_to]]

    for to in rule[cs_to]:
        if commodity:
            transfers.append(
                Transfer(to, commodity, price)
            )
        else:
            transfers.append(
                Transfer(to, None, None)
            )

    trans.trans_date = actual_date
    trans.labels = labels
    trans.properties = properties
    trans.comments = comments
    trans.name = name
    trans.transfers = transfers

    pass

def _apply_rules(transactions: List[Transaction], rules: Dict[str, Dict]) -> None:
    """
    Apply rules and process transactions

    :param transactions: list of transactions
    :param rules: rules to apply
    """

    # Assign rules
    matcher = [""] * len(transactions)
    for name, rule in rules.items():
        match = False
        for i, trans in enumerate(transactions):
            if len(matcher[i]) == 0:  # transaction not yet matched
                r = rule[cs_rule]

                if isinstance(r, dict):  # only single rule
                    match = _check_match(trans, r)

                elif isinstance(r, list):  # multiple options for matching possible
                    for ri in r:
                        match = _check_match(trans, ri)
                        if match:
                            break
                else:
                    raise ValueError("Rule definition {} not supported.".format(name))

                if match:
                    matcher[i] = name

    # Process rules and write
    for i, trans in enumerate(transactions):
        if len(matcher[i]) > 0:
            _process_transaction(trans, matcher[i], rules[matcher[i]])

def process_wallet(wallet: Wallet, rules: Dict[str, Dict], ) -> Wallet:
    """
    Write processed data to a file

    :param wallet: wallet to process
    :param rules: rules to assign transactions to accounts
    :return: processed wallet
    """
    _apply_rules(wallet.transactions, rules)


    return wallet
