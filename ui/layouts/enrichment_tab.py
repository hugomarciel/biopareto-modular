# ui/layouts/enrichment_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc
from services.gprofiler_service import get_organisms_from_api 
from services.reactome_service import ReactomeService

# Lista curada de Namespaces comunes
COMMON_NAMESPACES = [
    {'label': 'HGNC Symbol (Human Default)', 'value': 'HGNC'},
    {'label': 'Ensembl ID (ENSG/ENSMUSG)', 'value': 'ENSG'},
    {'label': 'UniProt/SwissProt (Proteins)', 'value': 'UNIPROTSWISSPROT'},
    {'label': 'Entrez Gene ID (NCBI)', 'value': 'ENTREZGENE_ACC'},
    {'label': 'RefSeq mRNA', 'value': 'REFSEQ_MRNA'},
    {'label': 'MGI (Mouse Only)', 'value': 'MGI'},
    {'label': 'RGD (Rat Only)', 'value': 'RGD'}
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

    # --- CONTROL PANEL (g:Profiler) ---
    control_panel = dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # 1. Organism Section
                dbc.Col([
                    dbc.Label("1. Organism", className="small text-uppercase text-muted fw-bold"),
                    dcc.Dropdown(
                        id='gprofiler-organism-dropdown', 
                        options=organism_options, 
                        value='hsapiens', 
                        placeholder="Select organism",
                        className="shadow-sm"
                    )
                ], width=12, md=4),
                
                # 2. ID Configuration Section
                dbc.Col([
                    dbc.Label("2. ID Configuration", className="small text-uppercase text-muted fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("Target Namespace"),
                        dbc.Select(
                            id='gprofiler-target-namespace',
                            options=COMMON_NAMESPACES,
                            value='HGNC',
                            className="shadow-sm"
                        ),
                    ], className="mb-2"),
                    
                    html.Div([
                        dbc.Switch(
                            id="gprofiler-validation-switch",
                            label="Standardize IDs (g:Convert)",
                            value=True,
                            className="d-inline-block fw-bold text-primary"
                        ),
                        #html.Span(" (Auto-fix gene names)", className="text-muted small ms-2")
                    ])
                ], width=12, md=5),

                # 3. Actions Section
                dbc.Col([
                    dbc.Label("Action", className="small text-uppercase text-muted fw-bold d-block"),
                    
                    html.Div([
                        # --- ICONO CORREGIDO: Usamos gráfico de barras (Estadística) ---
                        html.Div(
                            dcc.Loading(
                                id="loading-gprofiler-spinner", 
                                type="circle", 
                                color="#198754", # Verde (Success)
                                children=[
                                    # Objetivo oculto del callback
                                    html.Div(id="gprofiler-spinner-output", style={'display': 'none'}),
                                    # Icono visible por defecto (Gráfico de barras para análisis estadístico)
                                    html.I(
                                        className="bi bi-bar-chart-line-fill", 
                                        style={'fontSize': '2rem', 'color': '#198754'}, # Opacidad quitada para mejor visibilidad
                                        title="Statistical Analysis Ready"
                                    )
                                ]
                            ),
                            className="me-3 d-flex align-items-center justify-content-center",
                            style={'width': '40px'} 
                        ),
                        
                        # Botones
                        dbc.Button("🚀 Run Analysis", id="run-gprofiler-btn", color="success", disabled=True, className="me-2 shadow-sm flex-grow-1"),
                        dbc.Button("🗑️ Clear", id="clear-gprofiler-results-btn", color="secondary", outline=True, size="sm", disabled=True, className="shadow-sm")
                    ], className="d-flex align-items-center")
                    
                ], width=12, md=3, className="d-flex flex-column justify-content-end")
            ], className="g-3 mb-3"),

            html.Hr(className="my-2"),

            # 4. Data Sources
            dbc.Row([
                dbc.Col([
                    dbc.Label("3. Data Sources", className="small text-uppercase text-muted fw-bold"),
                    dbc.Checklist(
                        id='gprofiler-sources-checklist',
                        options=gprofiler_source_options,
                        value=default_sources,
                        inline=True,
                        inputClassName="me-2",
                        labelClassName="small",
                        style={'columnGap': '15px'}
                    )
                ], width=12)
            ])
        ])
    ], className="bg-light border-0 shadow-sm mb-4")

    return html.Div([
        control_panel,
        
        dcc.Loading(html.Div(id="gprofiler-results-content"), type="default"),
        
        html.Hr(), 
        dbc.Card([
            dbc.CardHeader(html.H6("Manhattan Plot: Functional Enrichment", className="fw-bold m-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.InputGroup([
                            dbc.InputGroupText("P-Value Threshold"),
                            dcc.Input(id='gprofiler-threshold-input', type='number', value=0.05, step=0.01, className="form-control")
                        ], size="sm")
                    ], width=4)
                ], className="mb-3"),
                dcc.Loading(dcc.Graph(id='gprofiler-manhattan-plot'), type="default")
            ])
        ], className="mt-3 mb-4 shadow-sm"), 
        
        dbc.Card([
            dbc.CardHeader(html.H6("Functional Clustergram", className="fw-bold m-0")),
            dbc.CardBody([dcc.Loading(html.Div(id='gprofiler-clustergram-output'), type="default")])
        ], className="mt-3 mb-4 shadow-sm"),
        
    ], className="mt-2")


def create_reactome_layout(organism_options):
    
    reactome_options = [
        {'label': 'Project to Human', 'value': 'projection'},
        {'label': 'Include Disease', 'value': 'disease'},
        {'label': 'Include Interactors', 'value': 'interactors'}
    ]
    default_reactome_values = ['projection', 'disease']

    # --- CONTROL PANEL (Reactome) ---
    control_panel = dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # 1. Organism
                dbc.Col([
                    dbc.Label("1. Organism", className="small text-uppercase text-muted fw-bold"),
                    dcc.Dropdown(
                        id='reactome-organism-input', 
                        options=organism_options, 
                        value='Homo sapiens', 
                        placeholder="Select organism",
                        className="shadow-sm"
                    )
                ], width=12, md=4),
                
                # 2. ID Config
                dbc.Col([
                    dbc.Label("2. ID Configuration", className="small text-uppercase text-muted fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("Target Namespace"),
                        dbc.Select(
                            id='reactome-target-namespace',
                            options=COMMON_NAMESPACES,
                            value='HGNC', 
                            className="shadow-sm"
                        ),
                    ], className="mb-2"),
                    
                    html.Div([
                        dbc.Switch(
                            id="reactome-validation-switch",
                            label="Standardize IDs",
                            value=True, 
                            className="d-inline-block fw-bold text-warning"
                        ),
                        #html.Span(" (Crucial for Reactome)", className="text-muted small ms-2")
                    ])
                ], width=12, md=5),

                # 3. Actions (Icono Pathway + Botones)
                dbc.Col([
                    dbc.Label("Action", className="small text-uppercase text-muted fw-bold d-block"),
                    
                    html.Div([
                        # --- Icono Diagrama/Pathway con Spinner ---
                        html.Div(
                            dcc.Loading(
                                id="loading-reactome-spinner", 
                                type="circle", 
                                color="#ffc107", # Amarillo (Warning/Reactome)
                                children=[
                                    html.Div(id="reactome-spinner-output", style={'display': 'none'}),
                                    html.I(
                                        className="bi bi-diagram-3", 
                                        style={'fontSize': '2rem', 'color': '#ffc107'},
                                        title="Pathway Analysis Ready"
                                    )
                                ]
                            ),
                            className="me-3 d-flex align-items-center justify-content-center",
                            style={'width': '40px'}
                        ),
                        
                        # Botones
                        dbc.Button("🚀 Run Analysis", id="run-reactome-btn", color="warning", disabled=True, className="me-2 shadow-sm flex-grow-1 text-white"),
                        dbc.Button("🗑️ Clear", id="clear-reactome-results-btn", color="secondary", outline=True, size="sm", disabled=True, className="shadow-sm")
                    ], className="d-flex align-items-center")
                    
                ], width=12, md=3, className="d-flex flex-column justify-content-end")
            ], className="g-3 mb-3"),

            html.Hr(className="my-2"),

            # 4. Options
            dbc.Row([
                dbc.Col([
                    dbc.Label("3. Analysis Options", className="small text-uppercase text-muted fw-bold"),
                    dbc.Checklist(
                        id="reactome-options-checklist",
                        options=reactome_options,
                        value=default_reactome_values,
                        inline=True,
                        inputClassName="me-2",
                        labelClassName="small",
                        style={'gap': '20px'}
                    ),
                ], width=12),
            ])
        ])
    ], className="bg-light border-0 shadow-sm mb-4")


    return html.Div([
        control_panel,
        
        dcc.Loading(html.Div(id="reactome-results-content"), type="default"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.Div(className="d-flex align-items-center justify-content-between", children=[
                        html.H6("Reactome Pathway Visualization", className="fw-bold m-0"), 
                        dcc.Loading(id="loading-reactome-diagram-spinner", children=html.Div(id="reactome-diagram-spinner-output"), type="circle")
                    ])), 
                    dbc.CardBody(html.Div(id='reactome-diagram-output', children=[
                        dbc.Alert("Select a pathway from the table above to visualize gene overlap.", color="light", className="text-center text-muted border-0")
                    ], className="p-1"))
                ], className="h-100 shadow-sm")
            ], width=12)
        ], className="g-4 mb-4 mt-2"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H6("Global Pathway Overview (Fireworks)", className="fw-bold m-0")), 
                    dbc.CardBody(html.Div(id='reactome-fireworks-output', children=[
                        dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="light", className="text-center text-muted border-0")
                    ], className="p-1"))
                ], className="h-100 shadow-sm")
            ], width=12)
        ], className="g-4"),
        
        dcc.Store(id='reactome-scroll-fix-dummy', data=0)
    ], className="mt-2")


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
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-intersect me-2"),
                            html.H4("Biological Enrichment Analysis", className="d-inline-block m-0")
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"),
                    
                    dbc.CardBody([
                        html.P("Select one or more solutions or gene groups from the Interest Panel to analyze the functional enrichment of their genes.", className="text-muted mb-4"),
                        
                        dbc.Card([
                            dbc.CardHeader("Selection Criteria", className="small text-uppercase fw-bold bg-light"),
                            dbc.CardBody([
                                html.Div(id='enrichment-visual-selector', children=[html.P("Loading items...", className="text-muted text-center py-4")]),
                                html.Div([
                                    dbc.Button("Clear Selection", id="clear-enrichment-selection-btn", color="danger", outline=True, size="sm", className="mt-2"),
                                ], id="clear-enrichment-btn-container", style={'display': 'none'})
                            ])
                        ], className="mb-4 border shadow-sm"),
                        
                        html.Div(id='enrichment-selection-panel', className="mb-4"),
                        
                        html.H5("Select Enrichment Service", className="mb-3 fw-bold text-dark"),
                        dbc.Tabs([
                            dbc.Tab(label="g:Profiler (GO, KEGG, REAC)", tab_id="gprofiler-tab", children=[create_gprofiler_layout(organism_options_gprofiler)], label_style={"fontWeight": "bold"}),
                            dbc.Tab(label="Reactome Pathways", tab_id="reactome-tab", children=[create_reactome_layout(organism_options_reactome)], label_style={"fontWeight": "bold"}),
                        ], id="enrichment-service-tabs", active_tab="gprofiler-tab", className="mb-3 nav-fill"),
                    ])
                ], className="shadow-sm border-0")
            ], width=12),
        ])
    ], fluid=True, className="py-3")