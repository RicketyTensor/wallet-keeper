import pandas
import numpy
import re
from pathlib import Path
from wallet_keeper.modules.translator.factory_reader import factory as factory_reader
from wallet_keeper.modules.translator.readers.reader_mobus_xml import ReaderMobusXML
from wallet_keeper.modules.core.wallet import Wallet

# global variables
wallet = Wallet()


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


def prepare(file: Path):
    global wallet

    reader = factory_reader.create(ReaderMobusXML.format)
    wallet.build(reader.read(Path(file)))

def get_transfers():
    global wallet

    # Get totals
    df, df_tags, df_properties, df_comments = wallet.get_pandas_transfers()

    return df, df_tags, df_properties, df_comments

def get_time_span():
    global wallet

    return wallet.get_time_span()

def get_accounts():
    global wallet

    return wallet.get_list_accounts()

def get_account_totals():
    global wallet

    # Get totals
    df = wallet.get_pandas_totals(value="price", hierarchy=True)

    return df


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

    # # Enhance dataframe
    # df["date"] = pandas.to_datetime(df["date"])
    # df["year"] = df.date.dt.year
    # df["quarter"] = df.date.dt.quarter
    # df["month"] = df.date.dt.month
    # df["day"] = df.date.dt.day
    #
    # # Update accounts
    # accounts = sorted(df["account"].unique())
    #
    # # Name properly
    # df_transactions = df.copy()
    #
    # # Create dataframes for tags
    # # ==========================
    # file_tags = "tags.dat"
    #
    # global_tags = []
    # with open(file_tags, "r") as f:
    #     lines = f.readlines()
    #     for line in lines:
    #         global_tags.append(line.strip())
    #
    # global_tags.insert(0, "Comment")
    #
    # df = df_transactions.apply(extract_tags, axis=1, result_type="expand", args=([global_tags]))
    # df.columns = global_tags
    # df_tags = df.copy()
    #
    # prefixes = ["Assets", "Equity", "Expenses", "Income", "Liabilities"]
    #
    # # Prepare dataframe of budget
    # # ===========================
    # file_budget = "budget.ledger"
    #
    # budget = []
    #
    # with open(file_budget, "r") as f:
    #     lines = f.readlines()
    #     period = "monthly"
    #     counter = 0
    #     for line in lines:
    #         # Decide period
    #         if "~ Monthly" in line:
    #             period = "m"
    #             counter += 1
    #         elif "~ Yearly" in line:
    #             period = "y"
    #             counter += 1
    #         else:
    #             if line.strip() in ["", "\n", "\r\n"]:
    #                 continue
    #
    #             # Start a new transaction
    #             if len(budget) < counter:
    #                 budget.append({
    #                     "account": [],
    #                     "monthly": [],
    #                     "yearly": [],
    #                     "currency": []
    #                 })
    #             entry = budget[-1]
    #             data = list(filter(None, line.strip().split(" ")))
    #             entry["account"].append(data[0])
    #             amount = None if len(data) < 2 else float(data[1])
    #             entry["currency"].append(None if len(data) < 3 else data[2])
    #             if period == "m":
    #                 entry["monthly"].append(amount)
    #                 entry["yearly"].append(0.0)
    #             elif period == "y":
    #                 entry["monthly"].append(0.0)
    #                 entry["yearly"].append(amount)
    #
    # # Balance all transactions
    # df = pandas.DataFrame()
    # for entry in budget:
    #     if entry["currency"].count(None) > 1:
    #         raise ValueError("Non-balancing transaction in a budget")
    #     elif entry["currency"].count(None) == 1:
    #         i = entry["currency"].index(None)
    #         m = [v for j, v in enumerate(entry["monthly"]) if j != i]
    #         y = [v for j, v in enumerate(entry["yearly"]) if j != i]
    #         entry["monthly"][i] = -sum(m)
    #         entry["yearly"][i] = -sum(y)
    #         entry["currency"][i] = entry["currency"][0]
    #     df = pandas.concat([df, pandas.DataFrame(entry)])
    #
    # df_budget = df.groupby(["account", "currency"]).sum(numeric_only=True).reset_index()
    #
    # # Prepare dataframe for prices
    # # ============================
    # file_history = "price.db"
    # df = pandas.read_csv(file_history, index_col=0, delimiter=",",
    #                      names=["date", "to_currency", "from_amount", "from_currency"]
    #                      ).reset_index()
    #
    # # Enhance dataframe
    # df["date"] = pandas.to_datetime(df["date"])
    # df["year"] = df.date.dt.year
    # df["quarter"] = df.date.dt.quarter
    # df["month"] = df.date.dt.month
    # df["day"] = df.date.dt.day
    #
    # # Name properly
    # df_prices = df.copy()
    #
    # pass
