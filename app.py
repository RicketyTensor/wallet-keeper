import dash
from dash import Dash, dcc, html, Input, Output, no_update, callback, clientside_callback
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

load_figure_template("flatly")

app = Dash(__name__, use_pages=True)

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink(page['name'], href=page["relative_path"]))
        for page in dash.page_registry.values()
    ],
    className="navbar navbar-expand-lg bg-dark",
    dark=True,
    links_left=True,
    fluid=True
)

app.layout = html.Div([
    navbar,
    dash.page_container
])

if __name__ == '__main__':
    app.run(debug=True)
