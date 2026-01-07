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

def _process_transfer(properties: Dict, rule: Dict, i: int) -> Transfer:
    """
    Process a transfer entry

    :param properties: properties attached to the transaction
    :param rule: rule for the transfer
    :param i: position of the transfer in the transaction
    :return: Transaction
    """
    account = rule[cs_account]
    message = properties[cs_message]
    amount = None
    price = None
    l = rule[cs_labels] if cs_labels in rule.keys() else []
    p = rule[cs_props] if cs_props in rule.keys() else {}
    c = rule[cs_comment] if cs_comment in rule.keys() else []

    # First transfer
    if i == 0:
        amount = Dosh(abs(properties[cs_amount]) * -1, properties[cs_currency])
        price = abs(amount)
    # Process commodities
    elif cs_commodity in rule.keys():
        pattern = rule[cs_commodity][cs_pattern]
        matches = re.findall(pattern, message.lower())
        if len(matches) < 1:
            pass
        else:
            match = matches[0].strip().replace(",", ".")
            commodity_amount = match
            commodity_name = rule[cs_commodity][cs_name]
            amount = Dosh(commodity_amount, commodity_name)

            pattern = rule[cs_price][cs_pattern]
            matches = re.findall(pattern, message.lower())
            if len(matches) < 1:
                print("WARNING: Pattern \"{}\" was not detected in the text \"{}\"".format(pattern, message))
                return None
            else:
                match = matches[0].strip().replace(",", ".")
                price_value = match
            price_currency = rule[cs_price][cs_name]
            price = round(Dosh(price_value, price_currency) * Dosh(commodity_amount, price_currency), 4)

    return Transfer(account, amount, price, l, p, c)

def _process_transaction(trans: Transaction, name: str, rule: Dict) -> None:
    """
    Make a processed ledger entry

    :param trans: transaction
    :param name: name for the transaction
    :param rule: rule to apply
    """
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

    # Transfers
    # =========
    # Note: First account in the list of transfers is to be deducted from
    for i, t in enumerate(rule[cs_transfers]):
        processed_trans = _process_transfer(trans.properties, t, i)
        if processed_trans is not None:
            transfers.append(processed_trans)
        else:
            return

    # Add tags
    if cs_tag in rule.keys():
        labels = rule[cs_tag]
    else:
        labels = []

    # Add properties
    if cs_props in rule.keys():
        properties.update(rule[cs_props])

    # Add requested fields
    if cs_fields in rule.keys():
        fields = rule[cs_fields]
        for f in fields:
            properties.update({f.capitalize(): str(trans.properties[f]).capitalize()})

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
