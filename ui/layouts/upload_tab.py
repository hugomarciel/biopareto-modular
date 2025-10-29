"""
Upload Tab Layout
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_upload_tab():
    """Create data upload tab"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("📁 Load Pareto Front Data", className="text-primary")),
                    dbc.CardBody([
                        html.P("Upload JSON files with Pareto front solutions.",
                               className="text-muted"),

                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                '📁 Drag and Drop or ',
                                html.A('Select JSON Files')
                            ]),
                            style={
                                'width': '100%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'margin': '10px'
                            },
                            multiple=True,
                            accept='.json'
                        ),

                        html.Hr(),

                        # Loaded fronts list section
                        html.Div([
                            html.H5("Loaded Fronts", className="mb-3"),
                            html.Div(id='fronts-list', children=[
                                html.P("No fronts loaded yet.", className="text-muted")
                            ])
                        ], className="mb-3"),

                        html.Hr(),

                        dbc.ButtonGroup([
                            dbc.Button("📥 Download Test File",
                                     id="download-test-btn",
                                     color="info",
                                     className="me-2"),
                            dbc.Button("🗑️ Clear Data",
                                     id="clear-data-btn",
                                     color="warning")
                        ], className="mb-3"),

                        dcc.Download(id="download-test-file"),

                        html.Hr(),

                        html.Div(id="upload-status", className="mt-3"),

                        # Information about expected format
                        dbc.Collapse([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📋 Expected JSON File Format:", className="text-info"),
                                    html.Pre('''[
  {
    "selected_genes": ["BRCA1", "TP53", "EGFR"],
    "accuracy": 0.92,
    "num_genes": 3,
    "solution_id": "Sol_1"
  },
  {
    "selected_genes": ["BRCA1", "TP53", "EGFR", "MYC"],
    "accuracy": 0.94,
    "num_genes": 4,
    "solution_id": "Sol_2"
  }
]''', style={'fontSize': '12px', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
                                ])
                            ])
                        ], id="format-info-collapse", is_open=False),

                        dbc.Button("ℹ️ View Format",
                                 id="toggle-format-info",
                                 color="link",
                                 size="sm",
                                 className="mt-2")
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)
