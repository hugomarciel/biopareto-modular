# ui/layouts/pareto_tab.py

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_pareto_tab():
    """Create Pareto front tab layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H5("Axis Configuration", className="text-secondary mb-0")
                            ]),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("X Axis:", className="fw-bold"),
                                        dcc.Dropdown(
                                            id='x-axis-dropdown',
                                            placeholder="Select X axis objective...",
                                            className="mb-2"
                                        ),
                                        html.Div(
                                            id='x-axis-static-text',
                                            className="text-muted",
                                            style={'display': 'none'}
                                        )
                                    ], width=5),
                                    dbc.Col([
                                        dbc.Label("Y Axis:", className="fw-bold"),
                                        dcc.Dropdown(
                                            id='y-axis-dropdown',
                                            placeholder="Select Y axis objective...",
                                            className="mb-2"
                                        ),
                                        html.Div(
                                            id='y-axis-static-text',
                                            className="text-muted",
                                            style={'display': 'none'}
                                        )
                                    ], width=5),
                                    dbc.Col([
                                        dbc.Label(" ", className="fw-bold d-block"),
                                        dbc.Button("⇄ Swap Axes",
                                                 id="swap-axes-btn",
                                                 color="info",
                                                 size="sm",
                                                 className="w-100")
                                    ], width=2)
                                ])
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H4(id="pareto-plot-title", className="text-primary mb-0")
                            ]),
                            dbc.CardBody([
                                # Añadido relayoutData para capturar zoom/pan
                                dcc.Graph(id='pareto-plot', style={'height': '500px'}, config={'responsive': True}),
                                html.Hr(),
                                html.Div([
                                    html.H6("Selection Actions:", className="text-info mb-3"),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Button("🗑️ Clear Selection",
                                                 id="clear-selection-btn",
                                                 color="danger",
                                                 size="sm",
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4),
                                        dbc.Col([
                                            dbc.Button("💾 Consolidate Selection To a New Front",
                                                 id="consolidate-selection-btn",
                                                 color="success",
                                                 size="sm",
                                                 disabled=True,
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4),
                                        dbc.Col([
                                            dbc.Button("↩️ Restore The Original Load",
                                                 id="restore-original-btn",
                                                 color="warning",
                                                 size="sm",
                                                 disabled=True,
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4)
                                    ], className="mb-3"),
                                    
                                    dbc.Button(
                                        "📌 Add All to Interest Panel",
                                        id="add-to-interest-btn",
                                        color="info",
                                        size="sm",
                                        disabled=True,
                                        className="w-100 mb-3"
                                    ),
                                    
                                    html.Hr(),
                                    
                                    html.H6("Selected Solutions:", className="text-info mb-3"),
                                    html.Small("Click on a point to select the solution. Also can use lasso/box to add more.",
                                             className="text-muted d-block mb-2"),
                                    html.Div(id="selected-solutions-info")
                                ])
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),
            ], width=12),
        ])
    ], fluid=True)