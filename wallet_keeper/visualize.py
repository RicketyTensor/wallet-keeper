import dash
from dash import Dash, dcc, html, Input, Output, no_update, callback, clientside_callback
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from wallet_keeper.modules.visualizer import processing
import argparse
from pathlib import Path
import os

load_figure_template("flatly")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='prepare',
        description='Visualize contents of a Mobus journal')
    parser.add_argument("file", help="Path to a Mobus journal file")
    args = parser.parse_args()

    processing.prepare(Path(args.file))
    # processing.assemble_dataframes()

    # Run application
    app = Dash(__name__, use_pages=True, pages_folder=os.path.join(os.path.dirname(__file__) + "/modules/visualizer"))

    navbar = dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink(page['name'], href=page["relative_path"]))
            for page in dash.page_registry.values()
        ],
        className="navbar navbar-expand-lg",
        dark=False,
        links_left=True,
        fluid=True
    )

    app.layout = html.Div([
        navbar,
        dash.page_container
    ])

    app.run(debug=True)
