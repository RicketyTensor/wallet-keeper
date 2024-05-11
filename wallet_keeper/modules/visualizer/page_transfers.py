import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas
from wallet_keeper.modules.visualizer import processing
import re
import calendar
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

dash.register_page(__name__, order=2, name="Transfer history")


def make_account_selector():
    accounts = processing.get_accounts()

    selector = dcc.Dropdown(
        accounts,
        id="transaction_account_selector_dropdown",
        placeholder="Select an account",
    )
    return html.Div([html.H5("Select accounts:"), selector])


def make_properties_filter():
    field = html.Div([
        html.H5("Filter properties using regex:"),
        dbc.Row(children=[
            dbc.Col([dcc.Dropdown(
                id="filter_prop_name",
                placeholder="Property to filter",
                options=[],
                className="dbc"
            )]),
            dbc.Col([dcc.Input(
                id="filter_prop_value",
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


@callback(
    Output('filtered_transactions', 'data'),
    Output('filtered_properties', 'data'),
    Input("filter_prop_name", "value"),
    Input("filter_prop_value", "value"),
    Input("transaction_account_selector_dropdown", "value"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def filter_transactions(tag, reg, selected, month_start, month_end):
    if not selected:
        return {}, {}

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    df, df_tags, df_properties, df_comments = processing.get_transfers(start_date=dmin, end_date=dmax)

    # Mask for account selection
    mask = df.account.isin(selected) if isinstance(selected, list) else df.account.isin([selected])
    df = df[mask]
    dfp = df_properties[mask]

    # Filter by property
    if tag:
        mask = df_tags[tag] != ""
        df = df[mask]
        dfp = dfp[mask]

    # Filter by regex
    if reg and tag and not reg.endswith("\\"):
        pattern = re.compile(reg)
        mask = df_tags[tag].apply(lambda x: len(re.findall(pattern, x)) > 0)
        df = df[mask]
        dfp = dfp[mask]

    return df.to_dict(orient="records"), dfp.to_dict(orient="records")


# Callback to show table of transactions
@callback(
    Output('history_click_data', 'children'),
    Input('history_graph', 'clickData'),
    Input("history_graph", "figure"),
    Input("filtered_transactions", "data"),
    Input("filtered_properties", "data"),
)
def display_click_data(click_data, fig, filtered_transactions, filtered_properties):
    if not filtered_transactions or not click_data:
        return []

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])

    dfp = pandas.DataFrame(filtered_properties)

    pt = click_data["points"][0]
    date = pt["x"]

    # Get name of the trace (account)
    trace = fig["data"][pt["curveNumber"]]["name"]

    # Generate mask
    mask = (df["date"] == date) & (df["account"] == trace)

    df = df[mask]
    entries = []
    for index, row in df.iterrows():
        amount = "{:.0f} {}".format(row["amount"], row["amount_currency"])
        price = "{:.0f} {}".format(row["price"], row["price_currency"])
        name = row["name"]
        entry = [dbc.Badge(price, className="badge bg-success", style={"margin-right": "10px"}),
                 dbc.Badge(name, className="badge bg-info")]
        entries.append(html.P(entry))

        if len(dfp) > 0:
            tags = dfp.iloc[index, :]
            rows = []
            for name, value in tags.items():
                if value:
                    rows.append(html.Tr([html.Td(name, style={"width": "100px"}), html.Td(value)]))

            if len(rows) > 0:
                table_body = [html.Tbody(rows)]
                table = dbc.Table(table_body, bordered=False)
                entries.append(table)

    return entries


# Graph callback
@callback(
    Output("history_graph", "figure"),
    Input("cumsum_switch", "value"),
    Input("filtered_transactions", "data"),
    Input("filtered_properties", "data"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def make_graph_history(cs, filtered_transactions, filtered_properties, month_start, month_end):
    if not filtered_transactions:
        return go.Figure()

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

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
                x=g["date"],
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

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_layout(title="Daily transfers")
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text=y.capitalize())
    fig.update_layout(clickmode='event+select')
    return fig


@callback(
    Output("bar_monthly_graph", "figure"),
    Input("filtered_transactions", "data"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def make_graph_monthly(filtered_transactions, month_start, month_end):
    if not filtered_transactions:
        return go.Figure()

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])
    df['year'] = df["date"].apply(lambda x: x.year)
    df['month'] = df["date"].apply(lambda x: x.month)

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

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_layout(title="Monthly delta")
    fig.update_xaxes(title_text="Month", row=1, col=1)
    fig.update_yaxes(title_text="Total", row=1, col=1)
    return fig


@callback(
    Output("bar_yearly_graph", "figure"),
    Input("filtered_transactions", "data"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def make_graph_yearly(filtered_transactions, month_start, month_end):
    if not filtered_transactions:
        return go.Figure()

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Generate dataframe
    df = pandas.DataFrame(filtered_transactions)
    df["date"] = pandas.to_datetime(df["date"])
    df['year'] = df["date"].apply(lambda x: x.year)

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

    fig.update_layout(title="Yearly totals")
    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_yaxes(title_text="Total", row=1, col=1)
    return fig


def make_month_selector():
    t0, t1 = processing.get_time_span()
    month_list = [i.strftime("%m/%Y") for i in pandas.date_range(start=t0, end=t1, freq='SMS', inclusive="both")]

    selector = dbc.Row(children=[
        dcc.Dropdown(
            month_list, month_list[0],
            id="select_month_range_start",
            placeholder="Start MM/YYYY",
            clearable=False
        ),
        dcc.Dropdown(
            month_list, month_list[-1],
            id="select_month_range_end",
            placeholder="End MM/YYYY",
            clearable=False
        )
    ])

    return html.Div([html.H5("Select date range:"), selector])


layout = dbc.Container(children=[
    dcc.Store(id="filtered_transactions"),
    dcc.Store(id="filtered_properties"),
    dbc.Row(children=[
        # Account selector
        dbc.Col(children=[
            make_account_selector(),
            make_month_selector(),
            make_properties_filter()
        ], width={"size": 2}),
        # Accounting
        dbc.Col(children=[
            html.H4("Plots"),
            graph_history,
            html.Div(id="history_click_data", children=[]),
            html.Div([dcc.Graph(id="bar_monthly_graph",
                                clear_on_unhover=False)
                      ]),
            html.Div([dcc.Graph(id="bar_yearly_graph",
                                clear_on_unhover=False)
                      ])
        ])
    ])
], fluid=True)
