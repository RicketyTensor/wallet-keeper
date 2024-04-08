import dash
from dash import dcc, html, Input, Output, callback, MATCH, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import datetime
import calendar
from dateutil.relativedelta import relativedelta
import pandas
from pages.dataframes import df_transactions, accounts, df_budget
from core.utils.colors import to_rgba

dash.register_page(__name__, order=3)


def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        raise Exception('lines do not intersect')

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


# Range slider for accounting
def get_first_and_last_day(t0, t1):
    d0 = t0.replace(day=1)
    r1 = calendar.monthrange(t1.year, t1.month)
    d1 = t1.replace(day=r1[1])
    return d0, d1


t0 = df_transactions["date"].min()
t1 = df_transactions["date"].max()
d0, d1 = get_first_and_last_day(t0, t1)
max_range = (d1.year - d0.year) * 12 + d1.month - d0.month
points = range(0, max_range + 1)
accounting_range = dbc.Row([
    html.Div("Accounting period:"),
    dcc.RangeSlider(min=points[0],
                    max=points[-1],
                    step=1,
                    value=[points[0], points[-1]],
                    id='budget_range',
                    marks={p: (d0 + relativedelta(months=p)).strftime("%m/%y")
                           for p in points},
                    allowCross=False
                    )
])

# Budget
# ======
budget_menu = dash_table.DataTable(
    id="budget_input_table",
    columns=[{
        "name": "{}".format(i.capitalize()),
        "id": i,
        "editable": True if i in ["account", "yearly", "monthly"] else False,
        "presentation": "dropdown" if i in ["account"] else "input",
        "deletable": False,
        "renamable": False
    } for i in df_budget.columns],
    data=df_budget.to_dict("records"),
    # editable=True,
    # row_deletable=True,
    dropdown={
        "account": {
            "options": [{
                "label": a,
                "value": a
            } for a in accounts]
        }
    },
    style_cell={'textAlign': 'left'},
)

budget_accs = list(df_budget.account.unique())

# Layout
# ======
layout = dbc.Container(
    children=[
        dcc.Store(id='data_monthly'),
        dcc.Store(id='data_budget'),
        dbc.Row([
            dbc.Col(children=[
                budget_menu
            ], width={"size": 4}),
            dbc.Col(children=[
                accounting_range,
                html.H4("Monthly development"),
                *[
                    dbc.Row(children=[
                        dbc.Col([dcc.Graph(id={"type": "budget_history_graph", "index": idx})], width=7),
                        dbc.Col([dcc.Graph(id={"type": "averages_graph", "index": idx})], width=5),
                    ])
                    for idx in range(len(budget_accs))]
                # todo: Make the shown figure dynamically dependent on the contents of the budget input table
            ], width={"size": 8})
        ]),
    ],
    fluid=True
)


@callback(
    Output('data_budget', 'data'),
    Input("budget_range", "value"),
    Input("budget_input_table", "derived_virtual_data"),
    Input("budget_input_table", "derived_virtual_selected_rows")
)
def filter_dataframe_budget(month_range, rows, derived_virtual_selected_rows):
    if derived_virtual_selected_rows is None:
        return pandas.DataFrame()

    if rows is None:
        return pandas.DataFrame()

    # Apply accounting range
    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])
    n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
    df = pandas.DataFrame({"date": [dmin + relativedelta(months=i) for i in range(n + 1)],
                           })

    df_complete = pandas.DataFrame()
    for i, row in enumerate(rows):
        a = row["account"]
        m = float(row["monthly"])
        y = float(row["yearly"])
        c = row["currency"]

        levels = a.split(":")
        n = len(levels)

        df_temp = df.copy()
        df_temp["account"] = a
        df_temp["monthly"] = m
        df_temp["yearly"] = y
        df_complete = pandas.concat([df_complete, df_temp])

    df_complete = df_complete.groupby(["date", "account"]).sum().reset_index()
    df_complete["total"] = df_complete["yearly"] / 12 + df_complete["monthly"]
    return df_complete.to_dict(orient="records")


# Dataframe for monthly analytics
@callback(
    Output('data_monthly', 'data'),
    Input("data_budget", "data"),
    Input("budget_range", "value"),
)
def filter_dataframe_monthly(data_budget, month_range):
    # Apply accounting range
    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])

    # Prepare dataframe
    df = df_transactions.copy()

    # Apply range
    df = df[df["date"].between(dmin, dmax, inclusive="both")].copy().reset_index()

    # Collapse months
    df = df.groupby(["year", "month", "account"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"])
    df['total'] = df.total.round(decimals=2)

    # Extend dataframe to include all months in the range
    n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
    df_monthly = pandas.DataFrame({"date": [dmin + relativedelta(months=i) for i in range(n + 1)],
                                   })
    df_monthly["year"] = df_monthly["date"].apply(lambda x: x.year)
    df_monthly["month"] = df_monthly["date"].apply(lambda x: x.month)
    df_monthly["total"] = 0.0

    df_complete = pandas.DataFrame()
    for a in df.account.unique():
        mask = df.account == a
        df_temp = df_monthly.copy()
        df_temp.loc[df_temp["date"].isin(df.loc[mask, "date"]), "total"] = df.loc[mask, "total"].values
        df_temp["account"] = a
        df_complete = pandas.concat([df_complete, df_temp])

    return df_complete.to_dict(orient='records')


# History graph
@callback(
    Output({"type": "budget_history_graph", "index": MATCH}, "figure"),
    Input('data_monthly', 'data'),
    Input('data_budget', 'data'),
    Input("budget_range", "value")
)
def display_history(data_monthly, data_budget, month_range):
    if not data_monthly:
        return go.Figure()

    idx = dash.callback_context.outputs_list['id']['index']  # get id of current callback

    dfb = pandas.DataFrame(data_budget)
    acc = budget_accs[idx]
    dfb["date"] = pandas.to_datetime(dfb["date"])
    dfb = dfb[dfb["account"] == acc].reset_index()

    dfm = pandas.DataFrame(data_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])
    dfm = dfm[dfm["account"] == acc].reset_index()

    # Generate figure
    y = "total"
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=dfm["date"],
            y=dfm["total"],
            name="Actuals"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dfb["date"],
            y=dfb["total"],
            name="Budget",
            mode="lines"
        )
    )

    delta = dfb.total.sum() - dfm.total.sum()
    if delta < 0:
        c = to_rgba("#e74c3c", 0.8)
    else:
        c = to_rgba("#00bc8c", 0.8)
    fig.add_annotation(
        x=0,
        y=1.15,
        xref="paper",
        yref="paper",
        text="{:.2f}".format(delta),
        align="left",
        showarrow=False,
        # bordercolor="#c7c7c7",
        # borderwidth=2,
        borderpad=5,
        bgcolor=c,
        opacity=0.8,
        font=dict(
            size=16,
        ),
    )

    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])
    fig.update_xaxes(range=[dmin - datetime.timedelta(days=30),
                            dmax + datetime.timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text=y.capitalize())
    fig.update_layout(title=budget_accs[idx])
    return fig


# Averages graph
@callback(
    Output({"type": "averages_graph", "index": MATCH}, "figure"),
    Input('data_monthly', 'data'),
    Input('data_budget', 'data'),
    Input("budget_range", "value"),
)
def display_averages(data_monthly, data_budget, month_range):
    if not data_monthly:
        return go.Figure()

    idx = dash.callback_context.outputs_list['id']['index']  # get id of current callback

    dfb = pandas.DataFrame(data_budget)
    acc = budget_accs[idx]
    dfb["date"] = pandas.to_datetime(dfb["date"])
    dfb = dfb[dfb["account"] == acc]

    dfm = pandas.DataFrame(data_monthly)
    dfm = dfm[dfm.account == acc]
    dfm["date"] = pandas.to_datetime(dfm["date"])

    # Generate figure
    fig = go.Figure()

    # Overall
    fig.add_trace(
        go.Box(y=dfm["total"], name="Overall", boxpoints='all')
    )

    # Last two year
    dmax = dfm.date.max()
    dmin = dmax - relativedelta(months=23)
    df = dfm[(dfm.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last 2 years", boxpoints='all')
    )

    # Last year
    dmax = dfm.date.max()
    dmin = dmax - relativedelta(months=11)
    df = dfm[(dfm.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last year", boxpoints='all')
    )

    # Last quarter
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=3)
    df = dfm[(dfm.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last quarter", boxpoints='all')
    )

    # This month
    df = df_transactions.copy()
    df = df[df.account == acc]
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=1)
    df = df[(df.date.between(dmin, dmax, inclusive="right"))]
    y = df["amount"].sum().round(decimals=2)

    fig.add_hline(
        y=y,
        line_dash="dot",
        label=dict(
            text="Last 30 days: {:.0f}".format(y),
            textposition="end",
            font=dict(size=14, color="white"),
            yanchor="top",
        ),
    )

    # Budget
    dmax = dfb.date.max()
    df = dfb[dfb.date == dmax]
    y = df["total"].sum().round(decimals=2)

    fig.add_hline(
        y=y,
        fillcolor="red",
        label=dict(
            text="Budget: {:.0f}".format(y),
            textposition="end",
            font=dict(size=14, color="red"),
            yanchor="top",
        ),
    )

    fig.update_yaxes(title_text="Monthly averages")
    return fig
