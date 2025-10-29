# ui/layouts/O_enrichment_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 


def create_O_enrichment_tab_modified(): # <-- FUNCIÓN RENOMBRADA
    """Create biological analysis tab with the new visual selector."""
    organism_options = get_organisms_from_api() 
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("🔬 O_Biological Enrichment Analysis antiguoooo", className="text-primary mb-0")
                    ]),
                    dbc.CardBody([
                        html.P("Select one or more solutions or gene groups from the Interest Panel to analyze the functional enrichment of their genes.",
                               className="text-muted"),

                        html.Hr(),

                        # START: Estructura Alineada con Grupos de Genes
                        html.Div([
                            html.H5("Select Items for Gene Aggregation:", className="mb-3"),
                            html.P("Genes from all selected items will be combined for the enrichment analysis.",
                                   className="text-muted small mb-3"),
                            
                            # ID donde se insertarán las tarjetas seleccionables (Output del callback)
                            html.Div(id='O_enrichment-visual-selector', children=[ # <-- ID RENOMBRADO
                                html.P("Loading items...", className="text-muted text-center py-4")
                            ])
                        ], className="mb-4"),
                        # END: Estructura Alineada con Grupos de Genes

                        # START: PANEL DE EDICIÓN DE SELECCIÓN (Genes combinados)
                        html.Div(id='O_enrichment-selection-panel'), # <-- ID RENOMBRADO
                        # END: PANEL DE EDICIÓN DE SELECCIÓN

                        html.Hr(),

                        html.Div([
                            dbc.Col([
                                dbc.Label("Select Organism:", className="fw-bold"),
                                dcc.Dropdown(
                                    id='O_organism-dropdown', # <-- ID RENOMBRADO
                                    options=organism_options, 
                                    value='hsapiens',
                                    placeholder="Select organism for enrichment analysis",
                                    className="mb-3"
                                )
                            ], width=6, className="mb-3"),

                            dbc.Button("🚀 Run Enrichment Analysis",
                                     id="O_run-enrichment-btn", # <-- ID RENOMBRADO
                                     color="success",
                                     disabled=True,
                                     className="mb-3")
                        ]),

                        html.Hr(),

                        dcc.Loading([
                            html.Div(id="O_enrichment-results") # <-- ID RENOMBRADO
                        ], type="default"),
                        
                    ])
                ])
            ], width=12),
        ])
    ], fluid=True)