# ui/layouts/enrichment_tab.py (REEMPLAZAR TODO)

import dash_bootstrap_components as dbc
from dash import html, dcc
# Asegúrate de que este servicio se haya importado correctamente en app.py para obtener organismos
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# --- Componente de Layout de g:Profiler ---
# ui/layouts/enrichment_tab.py (Fragmento con Manhattan Plot)

# --- Componente de Layout de g:Profiler ---
# ui/layouts/enrichment_tab.py (Fragmento con Manhattan Plot - REEMPLAZO COMPLETO)

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

        # 🔑 CONTENEDOR PARA EL MANHATTAN PLOT Y CONTROLES (DEBE ESTAR PRESENTE) 🔑
        dbc.Card([
            dbc.CardHeader(html.H4("Manhattan Plot: Functional Enrichment", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("P-Value Threshold (Gold Standard):"),
                        dcc.Input(
                            id='gprofiler-threshold-input',
                            type='number',
                            value=0.05, # Valor por defecto
                            min=0.0,
                            max=1.0,
                            step=0.001,
                            className="form-control mb-3"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Threshold Display Type:"),
                        dcc.Dropdown(
                            id='gprofiler-threshold-type-dropdown',
                            options=[
                                {'label': 'Bonferroni Corrected P-Value (Default)', 'value': 'bonferroni'},
                                {'label': 'User-defined P-Value', 'value': 'user'}
                            ],
                            value='bonferroni',
                            clearable=False,
                            className="mb-3"
                        )
                    ], width=8)
                ]),
                # 🔑 COMPONENTE DEL GRÁFICO (El Output que Dash no encuentra) 🔑
                dcc.Loading(
                    dcc.Graph(id='gprofiler-manhattan-plot', config={'displayModeBar': False}),
                    type="default"
                )
            ])
        ], className="mt-3 mb-4"),
        
        html.Hr(),
        # Área de resultados específica para g:Profiler (Tabla)
        dcc.Loading(
            html.Div(id="gprofiler-results-content"), 
            type="default"
        )
    ], className="mt-3")


# (El resto del contenido del archivo enrichment_tab.py se mantiene igual)


# ui/layouts/enrichment_tab.py (Función create_reactome_layout CORREGIDA Y ACTUALIZADA)

# ... (Las funciones create_gprofiler_layout y create_enrichment_tab_layout se mantienen)

# --- Componente de Layout de Reactome (CORREGIDO para layout vertical con Fireworks) ---
def create_reactome_layout(organism_options):
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Target Organism:", className="fw-bold"),
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
                dbc.Button("🗑️ Clear Results", id="clear-reactome-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=3)
        ], className="mb-3 align-items-end"),
        
        html.Hr(),
        
        # 1. CONTENEDOR DE VISUALIZACIÓN GLOBAL (FIREWORKS)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Global Pathway Overview (Fireworks)", className="mb-0")),
                    dbc.CardBody(className="", style={'padding': '5px 0 0 0'}), # Eliminamos padding excesivo
                        # 🔑 NUEVO CONTENEDOR PARA EL IFRAME DE FIREWORKS 🔑
                        html.Div(id='reactome-fireworks-output', children=[
                            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info")
                        ], className="p-1 border rounded")
                    
                ], className="h-100"),
            ], width=12) # Ocupa todo el ancho en la parte superior
        ], className="g-4 mb-4"), 
        
        # 2. CONTENEDOR DE RESULTADOS TABULARES
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    html.Div(id="reactome-results-content"), 
                    type="default"
                )
            ], width=12),
        ], className="g-4 mb-4"),
        
        # 3. CONTENEDOR DE VISUALIZACIÓN DEL DIAGRAMA (Abajo de la tabla)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Reactome Pathway Visualization (Data Overlay)", className="mb-0")),
                    
                    dbc.CardBody(className="", style={'padding': '5px 0 0 0'}), 
                        html.Div(id='reactome-diagram-output', children=[
                            dbc.Alert("Select a pathway from the table of results above to visualize the gene overlay.", color="secondary")
                        ], className="p-1 border rounded")
                    
                ], className="h-100"),
            ], width=12) 
        ], className="g-4")
        
    ], className="mt-3")


def create_enrichment_tab_modified(): 
    """Create biological analysis tab with internal tabs for Multi-API support."""
    
    # Manejar importación para gprofiler por si get_organisms_from_api no existe o falla
    try:
        organism_options_gprofiler = get_organisms_from_api() 
    except Exception:
        # Fallback si el servicio gprofiler no está disponible
        organism_options_gprofiler = [{'label': 'Homo sapiens', 'value': 'hsapiens'}]
        
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