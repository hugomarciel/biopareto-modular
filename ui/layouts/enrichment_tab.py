# ui/layouts/enrichment_tab.py (CÓDIGO COMPLETO CON CORRECCIÓN DE ORDEN DE MANHATTAN Y NUEVO CONTENEDOR DE HEATMAP)

import dash_bootstrap_components as dbc
from dash import html, dcc
# Asegúrate de que este servicio se haya importado correctamente en app.py para obtener organismos
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# ui/layouts/enrichment_tab.py (Fragmento con Manhattan Plot - ORDEN INVERTIDO)

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
                # Botón para limpiar resultados específicos
                dbc.Button("🗑️ Clear Results", id="clear-gprofiler-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=3)
        ], className="mb-3 align-items-end"),
        
        html.Hr(),

        # 1. Área de resultados específica para g:Profiler (Tabla) - AHORA ARRIBA
        dcc.Loading(
            html.Div(id="gprofiler-results-content"), 
            type="default"
        ),
        
        html.Hr(), # Separador entre la tabla y el gráfico

        # 2. CONTENEDOR PARA EL MANHATTAN PLOT Y CONTROLES - AHORA ABAJO
        dbc.Card([
            dbc.CardHeader(html.H4("Manhattan Plot: Functional Enrichment (Gold Standard Filter)", className="mb-0")),
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
                            # step='any', # Removido para permitir alta precisión
                            className="form-control mb-3"
                        )
                    ], width=3), 
                    # ❌ REMOVIDO: Threshold Display Type Dropdown
                ]),
                # COMPONENTE DEL GRÁFICO
                dcc.Loading(
                    # 🔑 CAMBIO CLAVE: Eliminar config={'displayModeBar': False} para activar herramientas 🔑
                    dcc.Graph(id='gprofiler-manhattan-plot'), 
                    type="default"
                )
            ])
        ], id="gprofiler-manhattan-card", className="mt-3 mb-4"), # Se añade ID al Card para un futuro control

        html.Hr(), # Separador entre Manhattan y Heatmap

        # 3. 🔑 NUEVO CONTENEDOR PARA EL CLUSTERGRAM/HEATMAP 🔑
        dbc.Card([
            dbc.CardHeader(html.H4("Functional Clustergram (Gene-Term Heatmap)", className="mb-0")),
            dbc.CardBody([
                dcc.Loading(
                    html.Div(id='gprofiler-clustergram-output'), # 🔑 ID CLAVE DEL OUTPUT 🔑
                    type="default"
                )
            ])
        ], id="gprofiler-clustergram-card", className="mt-3 mb-4"),
        
    ], className="mt-3")


# ui/layouts/enrichment_tab.py (Fragmento con la función create_reactome_layout)

# --- Componente de Layout de Reactome (CORREGIDO para layout vertical con nuevo orden y foco) ---
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
        
        # 1. 🔑 CONTENEDOR DE RESULTADOS TABULARES (AHORA EL PRIMERO) 🔑
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    html.Div(id="reactome-results-content"), 
                    type="default"
                )
            ], width=12),
        ], className="g-4 mb-4"),
        
        # 2. 🔑 CONTENEDOR DE VISUALIZACIÓN DEL DIAGRAMA (AHORA EL SEGUNDO) 🔑
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
        ], className="g-4 mb-4"),
        
        # 3. 🔑 CONTENEDOR DE VISUALIZACIÓN GLOBAL (FIREWORKS - AHORA EL TERCERO) 🔑
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Global Pathway Overview (Fireworks)", className="mb-0")),
                    dbc.CardBody(className="", style={'padding': '5px 0 0 0'}), 
                        # CONTENEDOR PARA EL IFRAME DE FIREWORKS
                        html.Div(id='reactome-fireworks-output', children=[
                            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info")
                        ], className="p-1 border rounded")
                    
                ], className="h-100"),
            ], width=12) 
        ], className="g-4"),
        dcc.Store(id='reactome-scroll-fix-dummy', data=0)
        
    ], className="mt-3")
# El resto del archivo create_enrichment_tab_modified() se mantiene igual

# ui/layouts/enrichment_tab.py (Función create_enrichment_tab_modified COMPLETAMENTE MODIFICADA)

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# --- Se mantienen create_gprofiler_layout y create_reactome_layout ---

# ui/layouts/enrichment_tab.py (Función create_enrichment_tab_modified COMPLETAMENTE MODIFICADA)

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# --- Se mantienen create_gprofiler_layout y create_reactome_layout ---

def create_enrichment_tab_modified(): 
    """Create biological analysis tab with internal tabs for Multi-API support."""
    
    try:
        organism_options_gprofiler = get_organisms_from_api() 
    except Exception:
        organism_options_gprofiler = [{'label': 'Homo sapiens', 'value': 'hsapiens'}]
        
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

                        # 1. Selector de Items (Selector de tarjetas)
                        html.Div([
                            html.H5("Select Items for Gene Aggregation:", className="mb-3"),

                            html.P("Genes from all selected items will be combined for the enrichment analysis.",
                                className="text-muted small mb-3"),

                            html.Div(id='enrichment-visual-selector', children=[
                                html.P("Loading items...", className="text-muted text-center py-4")
                            ])
                        ], className="mb-4"),

                        # 2. 🔑 BARRA DE BOTONES DE ACCIÓN (INSERCIÓN DIRECTA) 🔑
                        # Inserción directa en una fila de 12 para que ocupe el espacio deseado
                        dbc.Row([
                            dbc.Col([
                                # 🔑 CONTENEDOR DEL BOTÓN DE LIMPIEZA (Ubicación de la marca roja) 🔑
                                html.Div(
                                    dbc.Button("Clear Selection", 
                                        id="clear-enrichment-selection-btn", 
                                        color="secondary", 
                                        outline=True, 
                                        size="md", # Tamaño medio para coincidir
                                        className="me-2" # Margen derecho
                                    ),
                                    id="clear-enrichment-btn-container",
                                    # INICIALMENTE OCULTO
                                    style={'display': 'none', 'width': 'auto'} # Ajuste de ancho a contenido
                                ),
                            ], width=12, className="mb-4"), # Espacio debajo del selector de tarjetas
                        ]),
                        
                        # 3. PANEL DE RESUMEN DE SELECCIÓN (Justo debajo de la barra de acción)
                        html.Div(id='enrichment-selection-panel'),
                        
                        html.Hr(),

                        # 4. PESTAÑAS INTERNAS DE SERVICIOS (Se mantiene)
                        html.H5("Select Enrichment Service:", className="mb-3"),
                        dbc.Tabs([
                            dbc.Tab(label="g:Profiler (GO, KEGG, REAC)", tab_id="gprofiler-tab", children=[
                                create_gprofiler_layout(organism_options_gprofiler)
                            ]),
                            dbc.Tab(label="Reactome Pathways", tab_id="reactome-tab", children=[
                                create_reactome_layout(organism_options_reactome)
                            ]),
                        ], id="enrichment-service-tabs", active_tab="gprofiler-tab"),
                        
                    ])
                ])
            ], width=12),
        ])
    ], fluid=True)