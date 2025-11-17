# ui/layouts/enrichment_tab.py (CÓDIGO COMPLETO MODIFICADO)

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService


# --- Componente de Layout de g:Profiler (Sin cambios) ---
def create_gprofiler_layout(organism_options):
    
    gprofiler_source_options = [
        {'label': 'GO:BP (Biological Process)', 'value': 'GO:BP'},
        {'label': 'GO:MF (Molecular Function)', 'value': 'GO:MF'},
        {'label': 'GO:CC (Cellular Component)', 'value': 'GO:CC'},
        {'label': 'KEGG', 'value': 'KEGG'},
        {'label': 'Reactome (REAC)', 'value': 'REAC'},
        {'label': 'WikiPathways (WP)', 'value': 'WP'},
        {'label': 'Transfac (TF)', 'value': 'TF'},
        {'label': 'miRTarBase (MIRNA)', 'value': 'MIRNA'},
        {'label': 'Human Protein Atlas (HPA)', 'value': 'HPA'},
        {'label': 'CORUM', 'value': 'CORUM'},
        {'label': 'Human Phenotype Ontology (HP)', 'value': 'HP'},
    ]
    default_sources = ['GO:BP', 'GO:MF', 'GO:CC', 'KEGG', 'REAC']

    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Organism:", className="fw-bold"),
                dcc.Dropdown(id='gprofiler-organism-dropdown', options=organism_options, value='hsapiens', placeholder="Select organism for g:Profiler analysis", className="mb-3")
            ], width=5),
            dbc.Col([
                html.Div(className="d-flex align-items-center mb-3", style={'height': '38px'}, children=[
                    dbc.Button("🚀 Run g:Profiler Analysis", id="run-gprofiler-btn", color="success", disabled=True, className="me-2"),
                    html.Div(
                        style={'width': '38px', 'height': '38px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'},
                        children=[
                            dcc.Loading(
                                id="loading-gprofiler-spinner",
                                children=html.Div(id="gprofiler-spinner-output"),
                                type="circle",
                            )
                        ]
                    )
                ])
            ], width=5),
            dbc.Col([
                dbc.Button("🗑️ Clear Results", id="clear-gprofiler-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=2)
        ], className="mb-3 align-items-end"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Data Sources:", className="fw-bold"),
                dbc.Checklist(
                    id='gprofiler-sources-checklist',
                    options=gprofiler_source_options,
                    value=default_sources,
                    className="mb-3",
                    style={
                        'column-width': '240px', 
                        'padding-left': '20px' 
                    }
                )
            ], width=12)
        ], className="mb-3"),
        
        html.Hr(),
        dcc.Loading(html.Div(id="gprofiler-results-content"), type="default"),
        html.Hr(), 
        dbc.Card([
            dbc.CardHeader(html.H4("Manhattan Plot: Functional Enrichment (Gold Standard Filter)", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("P-Value Threshold (Gold Standard):"),
                        dcc.Input(id='gprofiler-threshold-input', type='number', value=0.05, min=0.0, max=1.0, step=0.01, className="form-control mb-3")
                    ], width=3), 
                ]),
                dcc.Loading(dcc.Graph(id='gprofiler-manhattan-plot'), type="default")
            ])
        ], id="gprofiler-manhattan-card", className="mt-3 mb-4"), 
        html.Hr(), 
        dbc.Card([
            dbc.CardHeader(html.H4("Functional Clustergram (Gene-Term Heatmap)", className="mb-0")),
            dbc.CardBody([
                dcc.Loading(html.Div(id='gprofiler-clustergram-output'), type="default")
            ])
        ], id="gprofiler-clustergram-card", className="mt-3 mb-4"),
        
    ], className="mt-3")

# --- Componente de Layout de Reactome (MODIFICADO) ---
#def # ui/layouts/enrichment_tab.py (SOLO LA FUNCIÓN MODIFICADA)

def create_reactome_layout(organism_options):
    
    # Definir opciones del Checklist
    reactome_options = [
        {'label': 'Project to Human (Inference)', 'value': 'projection'},
        {'label': 'Include Disease Pathways', 'value': 'disease'},
        {'label': 'Include IntAct Interactors', 'value': 'interactors'}
    ]
    
    # Valores por defecto (Proyección=ON, Enfermedad=ON, Interactores=OFF)
    default_reactome_values = ['projection', 'disease']

    return html.Div([
        # --- FILA 1: Organismo y Botones (Igual que g:Profiler) ---
        dbc.Row([
            # Columna 1: Selector de Organismo
            dbc.Col([
                dbc.Label("Select Target Organism:", className="fw-bold"),
                dcc.Dropdown(
                    id='reactome-organism-input', 
                    options=organism_options, 
                    value='Homo sapiens', 
                    placeholder="Select organism for Reactome analysis", 
                    className="mb-3"
                )
            ], width=5),
            
            # Columna 2: Botón Run + Spinner
            dbc.Col([
                html.Div(className="d-flex align-items-center mb-3", style={'height': '38px'}, children=[
                    dbc.Button("🚀 Run Reactome Analysis", id="run-reactome-btn", color="warning", disabled=True, className="me-2"),
                    html.Div(
                        style={'width': '38px', 'height': '38px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'},
                        children=[
                            dcc.Loading(
                                id="loading-reactome-spinner",
                                children=html.Div(id="reactome-spinner-output"), 
                                type="circle",
                            )
                        ]
                    )
                ])
            ], width=5),
            
            # Columna 3: Botón Clear
            dbc.Col([
                dbc.Button("🗑️ Clear Results", id="clear-reactome-results-btn", color="light", disabled=True, className="mb-3 w-100"),
            ], width=2)
        ], className="mb-3 align-items-end"),

        # --- FILA 2: Opciones de Análisis (Debajo, ancho completo) ---
        dbc.Row([
            dbc.Col([
                dbc.Label("Analysis Options:", className="fw-bold"),
                dbc.Checklist(
                    id="reactome-options-checklist",
                    options=reactome_options,
                    value=default_reactome_values,
                    inline=True, # 💡 Muestra las opciones horizontalmente
                    className="mb-2",
                    inputClassName="me-2", # Espaciado entre check y texto
                    style={'gap': '20px'} # Espaciado entre opciones
                ),
                #dbc.FormText("Default settings match Reactome Web behavior.", color="muted", className="small")
            ], width=12),
        ], className="mb-3"),
        
        html.Hr(),
        
        # --- Resultados y Visualizaciones (Sin cambios) ---
        dbc.Row([
            dbc.Col([dcc.Loading(html.Div(id="reactome-results-content"), type="default")], width=12),
        ], className="g-4 mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.Div(className="d-flex align-items-center", children=[
                            html.H4("Reactome Pathway Visualization (Data Overlay)", className="mb-0 me-2"),
                            html.Div(
                                style={'width': '30px', 'height': '30px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'},
                                children=[
                                    dcc.Loading(
                                        id="loading-reactome-diagram-spinner",
                                        children=html.Div(id="reactome-diagram-spinner-output"),
                                        type="circle",
                                    )
                                ]
                            )
                        ])
                    ),
                    
                    dbc.CardBody(className="", style={'padding': '5px 0 0 0'}), 
                        html.Div(id='reactome-diagram-output', children=[
                            dbc.Alert("Select a pathway from the table of results above to visualize the gene overlay.", color="secondary")
                        ], className="p-1 border rounded")
                    
                ], className="h-100"),
            ], width=12) 
        ], className="g-4 mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Global Pathway Overview (Fireworks)", className="mb-0")),
                    dbc.CardBody(className="", style={'padding': '5px 0 0 0'}), 
                        html.Div(id='reactome-fireworks-output', children=[
                            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info")
                        ], className="p-1 border rounded")
                ], className="h-100"),
            ], width=12) 
        ], className="g-4"),
        dcc.Store(id='reactome-scroll-fix-dummy', data=0)
        
    ], className="mt-3")


# --- Función principal (Sin cambios) ---
def create_enrichment_tab_modified(): 
    try:
        organism_options_gprofiler = get_organisms_from_api() 
    except Exception:
        organism_options_gprofiler = [{'label': 'Homo sapiens', 'value': 'hsapiens'}]
    organism_options_reactome = ReactomeService.get_reactome_organisms()
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.H4("🔬 Biological Enrichment Analysis", className="text-primary mb-0")]),
                    dbc.CardBody([
                        html.P("Select one or more solutions or gene groups from the Interest Panel to analyze the functional enrichment of their genes.", className="text-muted"),
                        html.Hr(),
                        html.Div([
                            html.H5("Select Items for Gene Aggregation:", className="mb-3"),
                            html.P("Genes from all selected items will be combined for the enrichment analysis.", className="text-muted small mb-3"),
                            html.Div(id='enrichment-visual-selector', children=[html.P("Loading items...", className="text-muted text-center py-4")])
                        ], className="mb-4"),
                        dbc.Row([
                            dbc.Col([
                                html.Div(
                                    [
                                        dbc.Button("Clear Selection", id="clear-enrichment-selection-btn", color="secondary", outline=True, size="md", className="me-2"),
                                    ],
                                    id="clear-enrichment-btn-container",
                                    style={'display': 'none', 'width': 'auto', 'vertical-align': 'middle'} 
                                ),
                            ], width=12, className="mb-4"), 
                        ]),
                        
                        html.Div(id='enrichment-selection-panel'),
                        
                        html.Hr(),
                        html.H5("Select Enrichment Service:", className="mb-3"),
                        dbc.Tabs([
                            dbc.Tab(label="g:Profiler (GO, KEGG, REAC)", tab_id="gprofiler-tab", children=[create_gprofiler_layout(organism_options_gprofiler)]),
                            dbc.Tab(label="Reactome Pathways", tab_id="reactome-tab", children=[create_reactome_layout(organism_options_reactome)]),
                        ], id="enrichment-service-tabs", active_tab="gprofiler-tab"),
                    ])
                ])
            ], width=12),
        ])
    ], fluid=True)