# ui/layouts/gene_groups_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_gene_groups_tab():
    """
    Create the Gene Groups Analysis tab with Standardized BioPareto UI.
    Includes comprehensive help guides for selection logic.
    """
    
    # --- 1. Popover de Ayuda: Main Guide (Lógica General) ---
    main_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Gene Groups Analysis Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("How selection works:"),
                    html.Span(" The analysis view adapts automatically based on the number of selected items:", className="small text-muted")
                ], className="mb-2"),

                # Lógica de Selección
                html.Div([
                    html.Ul([
                        html.Li([
                            html.Strong("1 Item: ", className="text-dark"), 
                            "Shows the gene list table only."
                        ], className="small text-muted"),
                        html.Li([
                            html.Strong("2-3 Items: ", className="text-dark"), 
                            "Generates a ", 
                            html.Strong("Venn Diagram", className="text-primary"), 
                            " and Frequency Chart. ",
                            html.Em("Note: Venn diagrams with 3+ sets may have visual geometric inconsistencies.", className="text-danger small")
                        ], className="small text-muted"),
                        html.Li([
                            html.Strong("4+ Items: ", className="text-dark"), 
                            "Switches to ", 
                            html.Strong("Matrix Cards", className="text-primary"), 
                            ". This system sorts intersections by complexity to handle high-dimensional data comfortably."
                        ], className="small text-muted"),
                    ], className="ps-3 mb-2")
                ]),

                html.Hr(className="my-2"),

                # Botones
                html.Div([
                    html.Strong("Actions:"),
                    html.Ul([
                        html.Li([
                            html.Code("Save Combined", className="text-success fw-bold"), 
                            ": Creates a new group containing the UNION of all selected genes."
                        ], className="small text-muted"),
                        html.Li([
                            html.Code("Clear", className="text-secondary fw-bold"), 
                            ": Instantly deselects all active cards."
                        ], className="small text-muted"),
                    ], className="ps-3 mb-0")
                ])
            ], style={'maxWidth': '450px'})
        ],
        id="gga-main-help-popover",
        target="gga-main-help-icon",
        trigger="legacy",
        placement="right",
    )

    return dbc.Container([
        
        # --- SECCIÓN 1: SELECTOR ---
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    # Header Estilizado
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-collection-play-fill me-2"),
                            html.H5("Gene Groups Selection", className="d-inline-block m-0 fw-bold"),
                            
                            # Icono Ayuda Principal
                            html.I(
                                id="gga-main-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="Click for analysis logic guide"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),

                    dbc.CardBody([
                        main_help_popover,
                        
                        html.P("Select items from your Interest Panel to analyze overlaps, intersections, and gene frequencies.",
                               className="text-muted small mb-4"),

                        html.Div(id='gene-groups-visual-selector', children=[
                            dbc.Alert([
                                html.I(className="bi bi-info-circle me-2"),
                                "Loading Interest Panel items..."
                            ], color="light", className="d-flex align-items-center small")
                        ])
                    ])
                ], className="shadow-sm border-0 mb-4")
            ], width=12)
        ]),

        # --- SECCIÓN 2: RESULTADOS DINÁMICOS ---
        # El contenido de aquí se genera en el callback (Gráficos, Tablas, Venn)
        html.Div(id='combined-genes-analysis-results')

    ], fluid=True, className="py-3")