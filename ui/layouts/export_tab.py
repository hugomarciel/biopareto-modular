import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table


def create_export_tab():
    """Create export tab layout."""
    layout = dbc.Container([
        # Selector de items
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-box2-heart me-2"),
                            html.H5("Select Items to Export", className="d-inline-block m-0 fw-bold"),
                            html.I(
                                id="export-main-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="How the export selection works"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),
                    dbc.CardBody([
                        dbc.Popover(
                            [
                                dbc.PopoverHeader("Export Selection Guide"),
                                dbc.PopoverBody([
                                    html.Div("Choose items from your Interest Panel, edit comments, and mark attachments to include in the export.", className="small text-muted"),
                                    html.Hr(className="my-2"),
                                    html.Ul([
                                        html.Li("Use the checkboxes to pick which items go into the report.", className="small text-muted"),
                                        html.Li("Comments can be edited and will be included in the export.", className="small text-muted"),
                                        html.Li("Attachments (tables/plots) will show toggles once available.", className="small text-muted")
                                    ], className="mb-0 ps-3")
                                ], style={'maxWidth': '420px'})
                            ],
                            id="export-main-help-popover",
                            target="export-main-help-icon",
                            trigger="legacy",
                            placement="right",
                        ),
                        html.P("Select items from your Interest Panel to prepare the export package.", className="text-muted small mb-4"),
                        html.Div(id='export-items-visual-selector', children=[
                            dbc.Alert([
                                html.I(className="bi bi-info-circle me-2"),
                                "No items yet. Add items to the Interest Panel first."
                            ], color="light", className="d-flex align-items-center small mb-0")
                        ])
                    ])
                ], className="shadow-sm border-0 mb-4")
            ], width=12)
        ]),

        # Detalle del item seleccionado
        dbc.Row([
            dbc.Col([
                html.Div(
                    dbc.Card([
                        dbc.CardHeader(
                            html.Div([
                                html.Div([
                                    html.I(className="bi bi-info-square-fill me-2"),
                                    html.H5("Item Details", className="d-inline-block m-0 fw-bold")
                                ], className="d-flex align-items-center text-primary"),
                                dbc.Button(
                                    "Download PDF",
                                    id="export-download-item-pdf",
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                    className="ms-auto"
                                ),
                                dcc.Download(id="export-item-pdf-download")
                            ], className="d-flex align-items-center gap-2"),
                            className="bg-white border-bottom position-relative"
                        ),
                        dbc.CardBody([
                            html.Div(id="export-selected-item-details", children=[
                                dbc.Alert([
                                    html.I(className="bi bi-hand-index me-2"),
                                    "Select an item above to see its details."
                                ], color="light", className="d-flex align-items-center small mb-0")
                            ]),
                            dbc.Alert([
                                html.Div([
                                    html.Label("Item Comment", className="fw-bold mb-1"),
                                    html.P("This comment will be included in the export.", className="small text-muted mb-2")
                                ], className="mb-2"),
                                dcc.Textarea(
                                    id="export-comment-editor",
                                    style={'minHeight': '120px'},
                                    className="form-control mb-2",
                                    placeholder="Add or edit the comment for this item..."
                                )
                            ], color="light", className="mt-3 border border-2"),
                            html.Hr(className="my-3"),
                            html.Div(id="export-attachments-preview", className="mt-1")
                        ])
                    ], className="shadow-sm border-0 mb-4"),
                    id="export-item-details-wrapper"
                )
            ], width=12)
        ]),

        # Bloque de exportaciones existentes
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("Export Results", className="text-primary mb-0")
                    ]),
                    dbc.CardBody([
                        html.P("Export analysis results in different formats or generate a full report.",
                               className="text-muted"),

                        # Complete report
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Complete Report", className="text-success"),
                                        html.P("Generate a detailed PDF/TXT report with data, plots, and enrichment results.",
                                               className="small text-muted"),
                                        dbc.ButtonGroup([
                                            dbc.Button("Generate PDF",
                                                     id="generate-pdf-report",
                                                     color="success",
                                                     className="me-2"),
                                            dbc.Button("Generate TXT",
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
                                        html.H6("Pareto Front Data", className="text-info"),
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
                                        html.H6("Gene List", className="text-info"),
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
                            html.H6("Current Session Summary:", className="text-secondary"),
                            html.Div(id="session-summary")
                        ])
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

    # Placeholder oculto para asegurar presencia de IDs usados en callbacks (Reactome table)
    hidden_placeholder = html.Div(
        dash_table.DataTable(
            id='enrichment-results-table-reactome',
            data=[],
            columns=[],
            style_table={'display': 'none'}
        ),
        style={'display': 'none'}
    )

    return html.Div([layout, hidden_placeholder])
