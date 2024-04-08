import dash
from dash import dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas
from pages.dataframes import df_transactions, prefixes, original_accounts
from core.utils.colors import to_rgba

dash.register_page(__name__, path='/', order=1)

df_totals = df_transactions.groupby(["account"]).agg({"amount": "sum"}).reset_index()
df_totals["amount"] = df_totals["amount"].round(decimals=2)


def display_bar_totals():
    df = df_totals
    fig = go.Figure(
        px.bar(
            df[df["account"].isin(prefixes)],
            x="account",
            y="amount",
            color="account",
            text_auto=True
        )
    )

    fig.update_layout(title="Current totals")
    fig.update_xaxes(title_text="Account")
    fig.update_yaxes(title_text="Amount")
    return fig


def account_to_levels(row):
    account = row.account
    levels = [None] * 3
    l = account.split(":")
    for i, a in enumerate(l):
        levels[i] = ":".join(l[:i + 1])

    return levels


def display_expenses_bars():
    df = df_totals.copy()
    df[["p0", "p1", "p2"]] = df.apply(account_to_levels, axis=1, result_type="expand")
    df = df[(df["p2"].isnull()) & df["p1"].notnull()]
    df["name"] = df["account"].apply(lambda x: x.split(":")[-1])

    name = "Expenses"
    mask = df.account.str.startswith(name)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[mask].name,
        y=df[mask].amount
    ))
    fig.update_traces(marker_color=px.colors.qualitative.Plotly[2])

    fig.update_layout(title="Expenses")
    fig.update_xaxes(title_text="Account")
    fig.update_yaxes(title_text="Amount")

    return fig


def display_accounts_sunburst():
    df = df_totals[df_totals.account.isin(original_accounts)].copy()
    df[["p0", "p1", "p2"]] = df.apply(account_to_levels, axis=1, result_type="expand")
    df["name"] = df["account"].apply(lambda x: x.split(":")[-1])
    df["parent"] = df["account"].apply(lambda x: ":".join(x.split(":")[:-1]))
    df["sign"] = df["amount"].apply(lambda x: -1 if x < 0 else 1)
    df["amount"] = df["amount"].abs()
    df["account"] = df["account"].apply(lambda x: x.replace(" ", "_"))

    dfg = df[df.p2.notnull()].groupby(["parent"]).agg({
        "amount": "sum",
        "p0": "first",
        "p1": "first"
    }).reset_index()
    dfg = dfg.rename(columns={"parent": "account"})
    dfg["name"] = dfg["account"].apply(lambda x: x.split(":")[-1])
    dfg["parent"] = dfg["account"].apply(lambda x: ":".join(x.split(":")[:-1]))
    dfg["sign"] = 1
    dfg["amount"] = dfg["amount"].round(2)

    df = pandas.concat([df, dfg])

    name = prefixes[2]
    df = df[(df.account.str.startswith(name)) & (df.p1.notnull())]
    df = df.sort_values("account")
    # df = df[df.amount > 1000]

    ids = list(df.account.apply(lambda x: ":".join(x.split(":")[1:])))
    parents = list(df.parent.apply(lambda x: ":".join(x.split(":")[1:])))
    labels = list(df.name)
    values = df.amount.values
    discrete_pattern = df.sign.apply(lambda x: "/" if x < 0 else "").values

    fig = go.Figure()
    fig.add_trace(go.Sunburst(
        labels=labels,  # mandatory
        ids=ids,  # optional
        parents=parents,  # mandatory
        values=values,  # mandatory
        # labels=[ "Eve", "Cain", "Seth", "Enos", "Noam", "Abel", "Awan", "Enoch", "Azura"],
        # parents=["",    "Eve",  "Eve",  "Seth", "Seth", "Eve",  "Eve",  "Awan",  "Eve" ],
        # values=[  65,    14,     12,     10,     2,      6,      6,      4,       4],
        branchvalues="total",
        marker={
            # "colors": color_discrete_sequence,
            "pattern": {"shape": discrete_pattern}
        }
    ))
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
    fig.update_layout(font_size=20,
                      height=1400)
    return fig


def display_accounts_radar():
    df = df_totals[df_totals.account.isin(original_accounts)].copy()
    df[["p0", "p1", "p2"]] = df.apply(account_to_levels, axis=1, result_type="expand")
    df["name"] = df["account"].apply(lambda x: x.split(":")[-1])
    df["parent"] = df["account"].apply(lambda x: ":".join(x.split(":")[:-1]))
    df["sign"] = df["amount"].apply(lambda x: -1 if x < 0 else 1)
    df["amount"] = df["amount"].abs()

    dfg = df[df.p2.notnull()].groupby(["parent"]).agg({
        "amount": "sum",
        "p0": "first",
        "p1": "first"
    }).reset_index()
    dfg = dfg.rename(columns={"parent": "account"})
    dfg["name"] = dfg["account"].apply(lambda x: x.split(":")[-1])
    dfg["parent"] = dfg["account"].apply(lambda x: ":".join(x.split(":")[:-1]))
    dfg["sing"] = 1

    df = pandas.concat([df, dfg])

    name = prefixes[2]
    df = df[(df.account.str.startswith(name)) & (df.p1.notnull()) & (df.p2.isnull())]

    labels = df.name
    values = df.amount

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True
            ),
        ),
        showlegend=False
    )

    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
    return fig


def display_accounts():
    df = df_totals.copy()
    df[["p0", "p1", "p2"]] = df.apply(account_to_levels, axis=1, result_type="expand")
    df["name"] = df["account"].apply(lambda x: x.split(":")[-1])

    sources = []
    targets = []
    values = []
    colors = []
    cmap = {p: px.colors.qualitative.Plotly[i] for i, p in enumerate(prefixes)}

    df["color"] = df["p0"].apply(lambda x: cmap[x])

    for i, row in df.iterrows():
        if not row.p1:
            continue
        elif not row.p2:
            sources.append(df.index[df.account == row.p0][0])
            targets.append(df.index[df.account == row.p1][0])
        else:
            sources.append(df.index[df.account == row.p1][0])
            targets.append(df.index[df.account == row.p2][0])
        values.append(row.amount)
        colors.append(to_rgba(cmap[row.p0], 0.5))

    fig = go.Figure()
    fig.add_trace(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=df.name,
            color=df.color
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors
        ))
    )

    fig.update_layout(font_size=20,
                      height=1800)
    return fig


layout = dbc.Container(children=[
    dbc.Row([
        dbc.Col(children=[dcc.Graph(figure=display_accounts())],
                width={"size": 5}),
        dbc.Col(children=[
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="overview_graph_totals", figure=display_bar_totals()),
                ], width=4),
                dbc.Col([
                    dcc.Graph(id="overview_graph_expenses", figure=display_expenses_bars())
                ], width=8)
            ]),
            dcc.Graph(id="overview_graph_sunburst", figure=display_accounts_sunburst())
        ], width={"size": 7})
    ])
], fluid=True)
