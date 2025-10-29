# ui/layouts/export_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_export_tab():
    """Create export tab layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("📤 Export Results", className="text-primary mb-0")
                    ]),
                    dbc.CardBody([
                        html.P("Export analysis results in different formats or generate a full report.",
                               className="text-muted"),

                        # Complete report
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("📋 Complete Report", className="text-success"),
                                        html.P("Generate a detailed PDF/TXT report with data, plots, and enrichment results.",
                                               className="small text-muted"),
                                        dbc.ButtonGroup([
                                            dbc.Button("📄 Generate PDF",
                                                     id="generate-pdf-report",
                                                     color="success",
                                                     className="me-2"),
                                            dbc.Button("📝 Generate TXT",
                                                     id="generate-txt-report",
                                                     color="info",
                                                     outline=True)
                                        ]),
                                        dcc.Download(id="pdf-report-download"),
                                        dcc.Download(id="txt-report-download"),
                                        html.Div(id="report-status", className="mt-2")
                                    ])
                                ])
                            ], width=12)
                        ], className="mb-3"),

                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("📊 Pareto Front Data", className="text-info"),
                                        html.P("Export current Pareto front solutions with their metrics.",
                                               className="small text-muted"),
                                        dbc.ButtonGroup([
                                            dbc.Button("CSV", id="btn-export-pareto-csv", color="primary", outline=True, className="me-1"),
                                            dbc.Button("JSON", id="btn-export-pareto-json", color="primary", outline=True)
                                        ]),
                                        dcc.Download(id="download-pareto-csv"),
                                        dcc.Download(id="download-pareto-json")
                                    ])
                                ])
                            ], width=6),

                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("🧬 Gene List", className="text-info"),
                                        html.P("Export complete list of unique genes found.",
                                               className="small text-muted"),
                                        dbc.ButtonGroup([
                                            dbc.Button("CSV", id="btn-export-genes-csv", color="success", outline=True, className="me-1"),
                                            dbc.Button("TXT", id="btn-export-genes-txt", color="success", outline=True)
                                        ]),
                                        dcc.Download(id="download-genes-csv"),
                                        dcc.Download(id="download-genes-txt")
                                    ])
                                ])
                            ], width=6)
                        ], className="mb-3"),

                        html.Hr(),

                        html.Div([
                            html.H6("📋 Current Session Summary:", className="text-secondary"),
                            html.Div(id="session-summary")
                        ])
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)