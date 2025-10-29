"""
Interest Panel Component
"""

import dash_bootstrap_components as dbc
from dash import html


def create_interest_panel():
    """Create the interest panel/annotation board"""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5("📌 Interest Panel", className="text-primary mb-0 d-inline-block"),
                dbc.Button(
                    "🗑️",
                    id="clear-interest-panel-btn",
                    color="link",
                    size="sm",
                    className="float-end",
                    title="Clear all items"
                )
            ])
        ]),
        dbc.CardBody([
            html.P("Save solutions, genes, and groups for later analysis",
                   className="text-muted small mb-3"),
            html.Div(id='interest-panel-content', children=[
                html.P("No items added yet", className="text-muted text-center py-4")
            ])
        ], style={'maxHeight': '600px', 'overflowY': 'auto'})
    ], className="sticky-top")
