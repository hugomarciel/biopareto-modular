# ui/layouts/enrichment_tab.py (REEMPLAZAR TODO)

import dash_bootstrap_components as dbc
from dash import html, dcc
# Asegúrate de que este servicio se haya importado correctamente en app.py para obtener organismos
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# --- Componente de Layout de g:Profiler ---
def create_gprofiler_layout(organism_options):
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Organism:", className="fw-bold"),
                dcc.Dropdown(id='gprofiler-organism-dropdown', options=organism_options, value='hsapiens', placeholder="Select organism for g:Profiler analysis", className="mb-3")
            ], width=6),
            dbc.Col([
                dbc.Button("🚀 Run g:Profiler Analysis", id="run-gprofiler-btn", color="success", disabled=True, className="mb-3 w-100"),
            ], width=3),
            dbc.Col([
                # NUEVO: Botón para limpiar resultados específicos
                dbc.Button("🗑️ Clear Results", id="clear-gprofiler-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=3)
        ], className="mb-3 align-items-end"),
        
        html.Hr(),
        # NUEVO: Área de resultados específica para g:Profiler
        dcc.Loading(
            html.Div(id="gprofiler-results-content"), 
            type="default"
        )
    ], className="mt-3")

# --- Componente de Layout de Reactome ---
def create_reactome_layout(organism_options):
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Target Organism:", className="fw-bold"),
                # CAMBIO: Usar dcc.Dropdown y organismo por defecto 'Homo sapiens'
                dcc.Dropdown(
                    id='reactome-organism-input', 
                    options=organism_options, 
                    value='Homo sapiens', 
                    placeholder="Select organism for Reactome analysis", 
                    className="mb-3"
                )
            ], width=6),
            dbc.Col([
                dbc.Button("🚀 Run Reactome Analysis", id="run-reactome-btn", color="warning", disabled=True, className="mb-3 w-100")
            ], width=3),
            dbc.Col([
                # NUEVO: Botón para limpiar resultados específicos
                dbc.Button("🗑️ Clear Results", id="clear-reactome-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=3)
        ], className="mb-3 align-items-end"),
        
        html.Hr(),
        # NUEVO: Área de resultados específica para Reactome
        dcc.Loading(
            html.Div(id="reactome-results-content"), 
            type="default"
        )
    ], className="mt-3")


def create_enrichment_tab_modified(): 
    """Create biological analysis tab with internal tabs for Multi-API support."""
    organism_options_gprofiler = get_organisms_from_api() 
    # NUEVA LLAMADA
    organism_options_reactome = ReactomeService.get_reactome_organisms()
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("🔬 Biological Enrichment Analysis", className="text-primary mb-0") 
                    ]),
                    dbc.CardBody([
                        html.P("Select one or more solutions or gene groups from the Interest Panel to analyze the functional enrichment of their genes.",
                               className="text-muted"),

                        html.Hr(),

                        # Selector de Items
                        html.Div([
                            html.H5("Select Items for Gene Aggregation:", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.P("Genes from all selected items will be combined for the enrichment analysis.",
                                        className="text-muted small mb-3"),
                                ], width=9),
                                dbc.Col([
                                    # NUEVO: Botón para limpiar la selección
                                    dbc.Button("🗑️ Clear Selection", 
                                        id="clear-enrichment-selection-btn", 
                                        color="danger", 
                                        size="sm", 
                                        className="w-100 mb-3"),
                                ], width=3)
                            ]),
                            html.Div(id='enrichment-visual-selector', children=[
                                html.P("Loading items...", className="text-muted text-center py-4")
                            ])
                        ], className="mb-4"),

                        # Panel de Resumen de Selección
                        html.Div(id='enrichment-selection-panel'), 

                        html.Hr(),

                        # PESTAÑAS INTERNAS DE SERVICIOS
                        html.H5("Select Enrichment Service:", className="mb-3"),
                        dbc.Tabs([
                            dbc.Tab(label="g:Profiler (GO, KEGG, REAC)", tab_id="gprofiler-tab", children=[
                                # CAMBIO: Pasar el listado de g:Profiler
                                create_gprofiler_layout(organism_options_gprofiler)
                            ]),
                            dbc.Tab(label="Reactome Pathways", tab_id="reactome-tab", children=[
                                # CAMBIO: Pasar el listado de Reactome
                                create_reactome_layout(organism_options_reactome)
                            ]),
                        ], id="enrichment-service-tabs", active_tab="gprofiler-tab"),
                        
                    ])
                ])
            ], width=12),
        ])
    ], fluid=True)