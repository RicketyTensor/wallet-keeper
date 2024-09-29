import pandas
import numpy
import re
from pathlib import Path
from wallet_keeper.modules.translator.factory_reader import factory as factory_reader
from wallet_keeper.modules.translator.readers.reader_mobus_xml import ReaderMobusXML
from wallet_keeper.modules.translator.readers.reader_ledger import ReaderLedger
from wallet_keeper.modules.core.wallet import Wallet
import calendar

# global variables
wallet = None

def prepare(file: Path):
    global wallet

    # reader = factory_reader.create(ReaderMobusXML.format)
    reader = factory_reader.create(ReaderLedger.format)
    wallet = reader.read(file)

# Establish account hierarchy
def get_hierarchy(words, delim=":"):
    groups = {}
    for word in words:
        if delim in word:
            split = word.split(delim)
            g = split[0]

            if g not in groups.keys():
                groups[g] = {}

            sub = [w.replace("{}{}".format(g, delim), "") for w in words if w.startswith(g)]
            groups[g] = get_hierarchy(sub)
        else:
            groups[word] = {}

    return groups


# Sum up container accounts
def sum_up_groups(groups, df, parents=None):
    df_new = pandas.DataFrame()
    if not parents:
        predecessors = []
    else:
        predecessors = parents

    if len(groups) == 0:
        for p in predecessors:
            df_child = df[df["account"] == predecessors[-1]].copy()
            df_child["account"] = p
            df_new = pandas.concat([df_new, df_child])
    else:
        for key, group in groups.items():
            if not parents:
                name = key
            else:
                name = ":".join([parents[-1], key])
            df_child = sum_up_groups(group, df, parents=[*predecessors, name])
            df_new = pandas.concat([df_new, df_child])

    return df_new


def extract_tags(row, all_tags):
    x = row["comment"]
    columns = [""] * len(all_tags)
    if x == x:
        text = x.replace("\\n", "").strip()
        tags = re.findall(r"\S*:\s", text)
        n = len(tags)
        for i, tag in enumerate(tags):
            if i == n - 1:
                value = re.findall(tags[i] + r"(.*)", text)[0].strip()
            else:
                value = re.findall(tags[i] + r"(.*)" + tags[i + 1], text)[0].strip()
            name = tag.replace(":", "").strip()
            columns[all_tags.index(name)] = value
            text = text.replace(tag, "")
            text = text.replace(value, "")

        columns[all_tags.index("Comment")] = text.strip()

    return columns


def explode_accounts(df: pandas.DataFrame):
    df_new = df.copy()

    # function to explode accounts
    def account_depth(row):
        return int(row.account.count(":"))

    # extend dataframe with account hierarchy
    df_new["depth"] = df.apply(account_depth, axis=1)
    df_new["parent"] = df_new.account.apply(lambda x: ":".join(x.split(":")[:-1]))
    df_new["name"] = df_new.account.apply(lambda x: x.split(":")[-1])  # make column with names to display

    return df_new


def get_transfers(start_date=None, end_date=None):
    global wallet

    # Get totals
    df, df_tags, df_properties, df_comments = wallet.get_pandas_transfers(start_date=start_date, end_date=end_date)

    # Enhance dataframe
    df["date"] = pandas.to_datetime(df["date"])
    df["year"] = df.date.dt.year
    df["quarter"] = df.date.dt.quarter
    df["month"] = df.date.dt.month
    df["day"] = df.date.dt.day

    return df, df_tags, df_properties, df_comments

def get_budgets():
    global wallet

    # Get frame
    dfm, dfy = wallet.get_pandas_budgets()

    return dfm, dfy


def get_time_span():
    global wallet

    return wallet.get_time_span()


def get_accounts():
    global wallet

    return wallet.get_list_accounts()

def get_accounts_w_budget():
    global wallet

    return sorted(wallet.get_list_accounts_w_budget())

def get_account_category(acc):
    global wallet

    return wallet.get_account_label(acc)


def get_account_totals(start_date=None, end_date=None, hierarchy=False):
    global wallet

    # Get totals
    df = wallet.get_pandas_totals(value="price", start_date=start_date, end_date=end_date, hierarchy=hierarchy)

    return df

def get_first_and_last_day(t0, t1):
    d0 = t0.replace(day=1)
    r1 = calendar.monthrange(t1.year, t1.month)
    d1 = t1.replace(day=r1[1])
    return d0, d1


# Prepare dataframe of transactions
# =================================
def assemble_dataframes():
    # Get totals
    df = get_account_totals()

    # Rebuild hierarchy backwards
    df["depth"] = df.account.apply(lambda x: x.count(":"))
    dfn = df.copy()

    for i in list(range(1, max(df.depth) + 1))[::-1]:
        mask = df.depth == i
        groups = df[mask].groupby(["account", "currency"])
        for name, group in groups:
            parent = ":".join(name[0].split(":")[:-1])
            dfg = group
            dfg.account = parent
            dfg.depth = i - 1
            dfn = pandas.concat([dfn, dfg])

    return dfn.groupby(["account", "currency", "depth"]).sum().reset_index()
