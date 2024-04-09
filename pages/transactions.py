import dash
from dash import dcc, html, Input, Output, no_update, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import datetime
import numpy
import pandas
from pages.preprocessing import df_transactions, df_tags, prefixes, accounts
import re

dash.register_page(__name__, order=2)

df = df_transactions.groupby("account").agg(
    total=pandas.NamedAgg(column="amount", aggfunc="sum")
).reset_index()
df.total = df.total.round(0)
df_accounts = df


def make_account_selector():
    df = df_accounts.copy()
    df.account = df.account.apply(lambda x: " : ".join(x.split(":")))

    table = dash_table.DataTable(
        id='account_selector_table',
        columns=[
            {"name": i.capitalize(), "id": i, "deletable": False, "selectable": True} for i in df.columns
        ],
        data=df.to_dict('records'),
        editable=False,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable=False,
        row_selectable="multi",
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="none",
        # page_current=0,
        # page_size=40,
        style_cell={'textAlign': 'left'},
        style_as_list_view=True,
        fixed_rows={'headers': True},
        style_table={'height': "1200px", "overflowY": "auto"},
    )
    return html.Div([html.H5("Select accounts:"), table])


def make_tag_filter():
    field = html.Div([
        html.H5("Filter tags using regex:"),
        dbc.Row(children=[
            dbc.Col([dcc.Dropdown(
                id="filter_tag_name",
                placeholder="Tag to filter",
                options=df_tags.columns
            )]),
            dbc.Col([dcc.Input(
                id="filter_tag_value",
                type="text",
                placeholder="regex pattern",
            )])
        ])
    ])
    return field


cumsum_switch = dcc.Checklist(
    id="cumsum_switch",
    options=[{"label": [html.Span("Cumulative sum", style={"padding-left": 10}),
                        ], "value": "cumsum"}]
)

graph_history = html.Div([
    cumsum_switch,
    dcc.Graph(id="history_graph",
              clear_on_unhover=False)
])

graph_bar_m = html.Div([dcc.Graph(id="bar_monthly_graph",
                                  clear_on_unhover=False)
                        ])

graph_bar_y = html.Div([dcc.Graph(id="bar_yearly_graph",
                                  clear_on_unhover=False)
                        ])

plots = [html.H4("Plots"),
         graph_history, html.Div(id="history_click_data", children=[]), graph_bar_m, graph_bar_y]

layout = dbc.Container(children=[
    dcc.Store(id="filtered_transactions"),
    dcc.Store(id="filtered_tags"),
    dbc.Row(children=[
        # Account selector
        dbc.Col(children=[make_account_selector(),
                          make_tag_filter()], width={"size": 3}),
        # Accounting
        dbc.Col(children=plots)
    ])
], fluid=True)


@callback(
    Output('filtered_transactions', 'data'),
    Output('filtered_tags', 'data'),
    Input("filter_tag_name", "value"),
    Input("filter_tag_value", "value"),
    Input("account_selector_table", "derived_virtual_data"),
    Input("account_selector_table", "derived_virtual_selected_rows")
)
def filter_transactions(tag, reg, rows, derived_virtual_selected_rows):
    if not derived_virtual_selected_rows:
        return {}, {}

    df = df_transactions.copy()
    dft = df_tags.copy()

    # Mask for account selection
    accs = []
    for i in derived_virtual_selected_rows:
        accs.append(df_accounts.account.iloc[i])
    mask = df.account.isin(accs)
    df = df[mask]
    dft = dft[mask]

    # Filter by tag
    if tag:
        mask = dft[tag] != ""
        df = df[mask]
        dft = dft[mask]

    # Filter by regex
    if reg and tag and not reg.endswith("\\"):
        pattern = re.compile(reg)
        mask = dft[tag].apply(lambda x: len(re.findall(pattern, x)) > 0)
        df = df[mask]
        dft = dft[mask]

    return df.to_dict(orient="records"), dft.to_dict(orient="records")


# Callback to show table of transactions
@callback(
    Output('history_click_data', 'children'),
    Input('history_graph', 'clickData'),
    Input("history_graph", "figure"),
    Input("filtered_transactions", "data"),
    Input("filtered_tags", "data"),
)
def display_click_data(click_data, fig, filtered_transactions, filtered_tags):
    if not filtered_transactions or not click_data:
        return []

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])

    dft = pandas.DataFrame(filtered_tags)

    pt = click_data["points"][0]
    date = pt["x"]

    # Get name of the trace (account)
    trace = fig["data"][pt["curveNumber"]]["name"]

    # Generate mask
    mask = (df["date"] == date) & (df["account"] == trace)

    df = df[mask]
    entries = []
    for index, row in df.iterrows():
        amount = "{:.0f} {}".format(row["amount"], row["currency"])
        name = row["name"]
        entry = [dbc.Badge(amount, className="badge bg-success", style={"margin-right": "10px"}),
                 dbc.Badge(name, className="badge bg-info")]
        entries.append(html.P(entry))

        tags = dft.iloc[index, :]
        rows = []
        for name, value in tags.items():
            if value:
                rows.append(html.Tr([html.Td(name, style={"width": "100px"}), html.Td(value)]))

        if len(rows) > 0:
            table_body = [html.Tbody(rows)]
            table = dbc.Table(table_body, bordered=False, className="table-dark")
            entries.append(table)

    return entries


# Graph callback
@callback(
    Output("history_graph", "figure"),
    Input("cumsum_switch", "value"),
    Input("filtered_transactions", "data")
)
def make_graph_history(cs, filtered_transactions):
    if not filtered_transactions:
        return go.Figure()

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])

    # Collapse to days
    df = df.groupby(["date", "account"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()

    # Compute cumulative sum
    df.loc[:, "cumulative sum"] = df.groupby(["account"]).total.cumsum()

    # Generate figure
    y = "total"
    if cs:
        if "cumsum" in cs:
            y = "cumulative sum"
    fig = go.Figure()
    for name, g in df.groupby(["account"]):
        fig.add_trace(
            go.Scatter(
                x=g.date,
                y=g[y],
                name=name[0],
                mode="lines+markers",
                marker=dict(
                    size=15,
                    line=dict(
                        width=2
                    )
                ),
            )
        )

    t0 = df_transactions.date.min()
    t1 = df_transactions.date.max()
    fig.update_layout(title="Transaction history")
    fig.update_xaxes(range=[t0 - datetime.timedelta(days=30),
                            t1 + datetime.timedelta(days=30)])
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text=y.capitalize())
    fig.update_layout(clickmode='event+select')
    return fig


@callback(
    Output("bar_monthly_graph", "figure"),
    Input("filtered_transactions", "data")
)
def make_graph_monthly(filtered_transactions):
    if not filtered_transactions:
        return go.Figure()

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])

    # Collapse to months
    df = df.groupby(["year", "month", "account"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"])

    fig = go.Figure(
        px.bar(
            df,
            x="date",
            y="total",
            color="account",
            barmode="group",
            text_auto=True
        )
    )

    t0 = df_transactions.date.min()
    t1 = df_transactions.date.max()
    fig.update_xaxes(range=[t0 - datetime.timedelta(days=30),
                            t1 + datetime.timedelta(days=30)])
    fig.update_layout(title="Monthly totals")
    fig.update_xaxes(title_text="Month", row=1, col=1)
    fig.update_yaxes(title_text="Total", row=1, col=1)
    return fig


@callback(
    Output("bar_yearly_graph", "figure"),
    Input("filtered_transactions", "data")
)
def make_graph_yearly(filtered_transactions):
    if not filtered_transactions:
        return go.Figure()

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])

    # Collapse to years
    df = df.groupby(["year", "account"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()
    df["date"] = df["year"]

    fig = go.Figure(
        px.bar(
            df,
            x="date",
            y="total",
            color="account",
            barmode="group",
            text_auto=True
        )
    )

    t0 = df_transactions.date.min()
    t1 = df_transactions.date.max()
    fig.update_layout(title="Yearly totals")
    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_yaxes(title_text="Total", row=1, col=1)
    return fig
