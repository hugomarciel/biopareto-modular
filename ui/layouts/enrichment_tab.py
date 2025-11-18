# ui/layouts/enrichment_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# Lista curada de Namespaces comunes para evitar llamar a la API innecesariamente
COMMON_NAMESPACES = [
    {'label': 'HGNC Symbol (Human Default)', 'value': 'HGNC'},
    {'label': 'Ensembl ID (ENSG/ENSMUSG)', 'value': 'ENSG'},
    {'label': 'UniProt/SwissProt (Proteins)', 'value': 'UNIPROTSWISSPROT'},
    {'label': 'Entrez Gene ID (NCBI)', 'value': 'ENTREZGENE_ACC'},
    {'label': 'RefSeq mRNA', 'value': 'REFSEQ_MRNA'},
    {'label': 'MGI (Mouse)', 'value': 'MGI'},
    {'label': 'RGD (Rat)', 'value': 'RGD'}
]

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
            # Columna 1: Organismo
            dbc.Col([
                dbc.Label("1. Select Organism:", className="fw-bold"),
                dcc.Dropdown(id='gprofiler-organism-dropdown', options=organism_options, value='hsapiens', placeholder="Select organism", className="mb-3")
            ], width=4),
            
            # Columna 2: Configuración de IDs (Namespace + Validación)
            dbc.Col([
                dbc.Label("2. ID Configuration:", className="fw-bold"),
                dbc.InputGroup([
                    dbc.InputGroupText("Target:"),
                    dbc.Select(
                        id='gprofiler-target-namespace',
                        options=COMMON_NAMESPACES,
                        value='HGNC', # Default HGNC
                        style={'maxWidth': '160px'}
                    ),
                ], className="mb-2"),
                
                dbc.Switch(
                    id="gprofiler-validation-switch",
                    label="Standardize IDs (g:Convert)",
                    value=True, # Default Activado
                    className="d-inline-block"
                ),
                html.Span(" Converts input to standard IDs.", className="text-muted small ms-2")
            ], width=5),

            # Columna 3: Botones de Acción
            dbc.Col([
                dbc.Label("Action:", className="fw-bold d-block"), # Espaciador visual
                html.Div(className="d-flex align-items-center mb-2", children=[
                    dbc.Button("🚀 Run Analysis", id="run-gprofiler-btn", color="success", disabled=True, className="me-2 w-100"),
                    html.Div(
                        style={'width': '30px', 'height': '30px'},
                        children=[dcc.Loading(id="loading-gprofiler-spinner", children=html.Div(id="gprofiler-spinner-output"), type="circle")]
                    )
                ]),
                dbc.Button("🗑️ Clear", id="clear-gprofiler-results-btn", color="light", size="sm", disabled=True, className="w-100"),
            ], width=3)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("3. Select Data Sources:", className="fw-bold"),
                dbc.Checklist(
                    id='gprofiler-sources-checklist',
                    options=gprofiler_source_options,
                    value=default_sources,
                    inline=True,
                    className="mb-3",
                    inputClassName="me-2",
                    style={'columnGap': '15px'}
                )
            ], width=12)
        ], className="mb-3"),
        
        html.Hr(),
        dcc.Loading(html.Div(id="gprofiler-results-content"), type="default"),
        # ... (Resto de plots: Manhattan, Clustergram se mantienen igual)
        html.Hr(), 
        dbc.Card([
            dbc.CardHeader(html.H4("Manhattan Plot: Functional Enrichment", className="mb-0")),
            dbc.CardBody([
                dbc.Row([dbc.Col([dbc.Label("P-Value Threshold:"), dcc.Input(id='gprofiler-threshold-input', type='number', value=0.05, step=0.01, className="form-control")], width=3)]),
                dcc.Loading(dcc.Graph(id='gprofiler-manhattan-plot'), type="default")
            ])
        ], className="mt-3 mb-4"), 
        html.Hr(), 
        dbc.Card([
            dbc.CardHeader(html.H4("Functional Clustergram", className="mb-0")),
            dbc.CardBody([dcc.Loading(html.Div(id='gprofiler-clustergram-output'), type="default")])
        ], className="mt-3 mb-4"),
        
    ], className="mt-3")


def create_reactome_layout(organism_options):
    
    reactome_options = [
        {'label': 'Project to Human', 'value': 'projection'},
        {'label': 'Include Disease', 'value': 'disease'},
        {'label': 'Include Interactors', 'value': 'interactors'}
    ]
    default_reactome_values = ['projection', 'disease']

    return html.Div([
        dbc.Row([
            # Columna 1: Organismo
            dbc.Col([
                dbc.Label("1. Select Organism:", className="fw-bold"),
                dcc.Dropdown(id='reactome-organism-input', options=organism_options, value='Homo sapiens', placeholder="Select organism", className="mb-3")
            ], width=4),
            
            # Columna 2: Configuración de IDs
            dbc.Col([
                dbc.Label("2. ID Configuration:", className="fw-bold"),
                dbc.InputGroup([
                    dbc.InputGroupText("Target:"),
                    dbc.Select(
                        id='reactome-target-namespace',
                        options=COMMON_NAMESPACES,
                        value='UNIPROT', # Default UNIPROT para Reactome (Mejor práctica)
                        style={'maxWidth': '160px'}
                    ),
                ], className="mb-2"),
                
                dbc.Switch(
                    id="reactome-validation-switch",
                    label="Standardize IDs",
                    value=True, 
                    className="d-inline-block"
                ),
                html.Span(" Recommended for Reactome.", className="text-muted small ms-2")
            ], width=5),

            # Columna 3: Botones
            dbc.Col([
                dbc.Label("Action:", className="fw-bold d-block"),
                html.Div(className="d-flex align-items-center mb-2", children=[
                    dbc.Button("🚀 Run Analysis", id="run-reactome-btn", color="warning", disabled=True, className="me-2 w-100"),
                    html.Div(
                        style={'width': '30px', 'height': '30px'},
                        children=[dcc.Loading(id="loading-reactome-spinner", children=html.Div(id="reactome-spinner-output"), type="circle")]
                    )
                ]),
                dbc.Button("🗑️ Clear", id="clear-reactome-results-btn", color="light", size="sm", disabled=True, className="w-100"),
            ], width=3)
        ], className="mb-3"),

        # Fila 2: Opciones
        dbc.Row([
            dbc.Col([
                dbc.Label("3. Analysis Options:", className="fw-bold"),
                dbc.Checklist(
                    id="reactome-options-checklist",
                    options=reactome_options,
                    value=default_reactome_values,
                    inline=True,
                    className="mb-2",
                    inputClassName="me-2",
                    style={'gap': '20px'}
                ),
            ], width=12),
        ], className="mb-3"),
        
        html.Hr(),
        # ... (Resto de visualizaciones se mantienen igual)
        dbc.Row([dbc.Col([dcc.Loading(html.Div(id="reactome-results-content"), type="default")], width=12)], className="g-4 mb-4"),
        dbc.Row([dbc.Col([dbc.Card([dbc.CardHeader(html.Div(className="d-flex align-items-center", children=[html.H4("Reactome Pathway Visualization", className="mb-0 me-2"), dcc.Loading(id="loading-reactome-diagram-spinner", children=html.Div(id="reactome-diagram-spinner-output"), type="circle")])), dbc.CardBody(html.Div(id='reactome-diagram-output', children=[dbc.Alert("Select a pathway above.", color="secondary")], className="p-1 border rounded"))], className="h-100")], width=12)], className="g-4 mb-4"),
        dbc.Row([dbc.Col([dbc.Card([dbc.CardHeader(html.H4("Global Pathway Overview (Fireworks)", className="mb-0")), dbc.CardBody(html.Div(id='reactome-fireworks-output', children=[dbc.Alert("Run analysis to view.", color="info")], className="p-1 border rounded"))], className="h-100")], width=12)], className="g-4"),
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