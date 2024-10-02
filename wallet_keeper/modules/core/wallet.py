import pandas
from typing import List, Dict
from wallet_keeper.modules.core.transaction import Transaction
from copy import copy, deepcopy
import datetime


class Wallet(object):
    def __init__(self, transactions: List[Transaction], account: Dict[str, str] = None,
                 budget_monthly: Transaction = None, budget_yearly: Transaction = None):
        self.transactions = transactions
        self.account_labels = account
        self.budget_monthly = budget_monthly
        self.budget_yearly = budget_yearly

        pass

    def _extract_accounts(self):
        """
        Get accounts present in the journal

        :return:
        """
        accounts = []
        for t in self.transactions:
            accounts.extend([tt.account for tt in t.transfers])

        return sorted(list(set(accounts)))

    def get_list_accounts(self) -> List[str]:
        """
        Get list of accounts

        :return:
        """
        return list(self.account_labels.keys())

    def get_list_accounts_w_budget(self) -> List[str]:
        """
        Get list of accounts

        :return:
        """

        accs = list({tt.account for tt in self.budget_monthly.transfers + self.budget_yearly.transfers})

        return accs

    def get_account_label(self, acc: str) -> str:
        """
        Get category of an account

        :return:
        """
        return self.account_labels[acc]

    def get_pandas_transfers(self, start_date=None, end_date=None):
        """
        Get DataFrame of transfers

        :param start_date: first day from which transfers should be considered
        :param end_date: last day up to which transfers should be considered
        :return: DataFrames with transfers, tags, properties and comments
        """

        data = []
        tags = []
        properties = []
        comments = []
        for t in self.transactions:
            # Change if in range
            if start_date:
                if start_date > t.trans_date:
                    continue

            if end_date:
                if t.trans_date > end_date:
                    continue

            # Add transfers
            data.extend([(tt.account, self.account_labels[tt.account], t.trans_date, t.book_date, t.name,
                          tt.amount.value, tt.amount.currency,
                          tt.price.value, tt.price.currency) for tt in t.transfers])

            t_tags = {k: True for k in t.labels}
            t_props = t.properties
            t_comments = ["\n".join(t.comments)]

            for tt in t.transfers:
                tt_tags = copy(t_tags)
                tt_tags.update({k: True for k in tt.labels})

                tt_props = copy(t_props)
                tt_props.update(tt.properties)

                tt_comments = copy(t_comments)
                tt_comments.extend(["\n"] + ["\n".join(tt.comments)])

                tags.append(tt_tags)
                properties.append(tt_props)
                comments.append(tt_comments)

        # Transfer to dataframes
        df = pandas.DataFrame(data, columns=["account", "category", "date", "booking_date", "name", "amount",
                                             "amount_currency",
                                             "price", "price_currency"])
        df_tags = pandas.DataFrame(tags)
        df_properties = pandas.DataFrame(properties)
        df_comments = pandas.DataFrame(comments)

        return df, df_tags, df_properties, df_comments

    def get_pandas_budgets(self) -> (pandas.DataFrame, pandas.DataFrame):
        """
        Get dataframes with budget information

        :return:
        """
        data = [[tt.account, tt.amount.value, tt.amount.currency,
                 tt.price.value, tt.price.currency] for tt in self.budget_monthly.transfers]
        dfm = pandas.DataFrame(data, columns=["account", "amount", "amount_currency", "price", "price_currency"])

        data = [[tt.account, tt.amount.value, tt.amount.currency,
                 tt.price.value, tt.price.currency] for tt in self.budget_yearly.transfers]
        dfy = pandas.DataFrame(data, columns=["account", "amount", "amount_currency", "price", "price_currency"])

        return dfm, dfy

    def get_time_span(self) -> (datetime.datetime, datetime.datetime):
        """
        Get time span of available data

        :return:
        """
        dates = [t.trans_date for t in self.transactions]

        return min(dates), max(dates)

    def get_pandas_totals(self, value="amount", start_date=None, end_date=None, hierarchy: bool = False):
        """
        Sum up account totals

        :param value: ["amount", "price"] value type to sum up
        :param start_date: first day from which transfers should be considered
        :param end_date: last day up to which transfers should be considered
        :param hierarchy: a flag to include hierarchy with parent accounts
        :return: DataFrame with totals for each account
        """
        if value not in ["amount", "price"]:
            raise ValueError("Unknown argument value {} in get_pandas_totals()".format(value))

        data = []
        for t in self.transactions:
            # Change if in range
            if start_date:
                if start_date > t.trans_date:
                    continue

            if end_date:
                if t.trans_date > end_date:
                    continue

            data.extend([(tt.account, tt.__getattribute__(value).value, tt.__getattribute__(value).currency)
                         for tt in t.transfers])

        df = pandas.DataFrame(data, columns=["account", "amount", "currency"])
        df = df.groupby(["account", "currency"]).sum().reset_index()

        if hierarchy:
            df["parent"] = ""
            # Rebuild hierarchy backwards
            df["depth"] = df.account.apply(lambda x: x.count(":"))

            for i in list(range(1, max(df.depth) + 1))[::-1]:
                mask = df.depth == i
                groups = df[mask].groupby(["account", "currency"])
                for name, group in groups:
                    parent = ":".join(name[0].split(":")[:-1])
                    df.loc[df.account == name[0], "parent"] = parent
                    dfg = group
                    dfg.account = parent
                    dfg.depth = i - 1
                    df = pandas.concat([df, dfg])

            return df.groupby(["account", "currency"]).agg({
                "amount": "sum",
                "depth": "first",
                "parent": "first"
            }).reset_index()

        else:
            return df.groupby(["account", "currency"]).agg({
                "amount": "sum"
            }).reset_index()
