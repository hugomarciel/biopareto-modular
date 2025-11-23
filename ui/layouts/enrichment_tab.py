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
    """Layout for g:Profiler service with Standardized UI and Help"""
    
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

    # --- Popover: Manhattan Plot Help ---
    manhattan_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Manhattan Plot Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("What it shows:"), 
                    html.Span(" Functional terms grouped by source. The Y-axis shows statistical significance (-log10 P-value). Higher points = More significant.", className="small text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Navigation:"),
                    html.Ul([
                        html.Li("Scroll Mouse: Zoom In/Out (Y-axis)."),
                        html.Li("Click & Drag: Pan/Move across the plot."),
                        html.Li("Double Click: Reset view."),
                    ], className="small text-muted ps-3 mb-2")
                ]),

                html.Div([
                    html.Strong("Filtering:"), 
                    html.Span(" The P-Value Threshold filter below affects this plot, the results table, and the heatmap simultaneously.", className="small text-muted")
                ], className="mb-0")
            ], style={'maxWidth': '350px'})
        ],
        id="manhattan-help-popover",
        target="manhattan-help-icon",
        trigger="legacy",
        placement="left",
    )

    # --- Popover: Clustergram Help ---
    clustergram_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Functional Clustergram Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("What it shows:"), 
                    html.Span(" A Heatmap relating Genes (Columns) to Enriched Terms (Rows).", className="small text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Color Scale:"), 
                    html.Span(" Indicates the strength of association or significance (-log10 p-value).", className="small text-muted")
                ], className="mb-2"),

                html.Div([
                    html.Strong("Clustering:"), 
                    html.Span(" Rows and columns are automatically reordered using hierarchical clustering to group similar functional profiles together.", className="small text-muted")
                ], className="mb-0")
            ], style={'maxWidth': '350px'})
        ],
        id="clustergram-help-popover",
        target="clustergram-help-icon",
        trigger="legacy",
        placement="left",
    )

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
                            label="Standardize IDs (use g:Convert)",
                            value=True,
                            className="d-inline-block fw-bold text-primary"
                        ),
                    ])
                ], width=12, md=5),

                # 3. Actions Section
                dbc.Col([
                    dbc.Label("Action", className="small text-uppercase text-muted fw-bold d-block"),
                    
                    html.Div([
                        # --- ICONO DE ESTADÍSTICA ---
                        html.Div(
                            dcc.Loading(
                                id="loading-gprofiler-spinner", 
                                type="circle", 
                                color="#198754", 
                                children=[
                                    html.Div(id="gprofiler-spinner-output", style={'display': 'none'}),
                                    html.I(
                                        className="bi bi-bar-chart-line-fill", 
                                        style={'fontSize': '2rem', 'color': '#198754'}, 
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
        
        # Results Table Container (Generated in Callback)
        dcc.Loading(html.Div(id="gprofiler-results-content"), type="default"),
        
        html.Hr(className="my-4"), 
        
        # --- Manhattan Plot Card ---
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="bi bi-graph-up me-2"),
                    html.H6("Manhattan Plot: Functional Enrichment", className="d-inline-block m-0 fw-bold"),
                    html.I(
                        id="manhattan-help-icon",
                        className="bi bi-question-circle-fill text-muted ms-2",
                        style={'cursor': 'pointer', 'fontSize': '1rem'}
                    )
                ], className="d-flex align-items-center text-primary")
            ], className="bg-white border-bottom"),
            
            dbc.CardBody([
                manhattan_help_popover,
                
                dbc.Row([
                    dbc.Col([
                        dbc.InputGroup([
                            dbc.InputGroupText("P-Value Threshold"),
                            dcc.Input(id='gprofiler-threshold-input', type='number', value=0.05, step=0.01, className="form-control")
                        ], size="sm")
                    ], width=12, md=4)
                ], className="mb-3"),
                
                dcc.Loading(
                    dcc.Graph(
                        id='gprofiler-manhattan-plot',
                        config={
                            'scrollZoom': True,  
                            'responsive': True,  
                            'displayModeBar': True 
                        }
                    ), 
                    type="default"
                )
            ])
        ], className="mb-4 shadow-sm border-0"), 
        
        # --- Clustergram Card ---
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="bi bi-grid-3x3-gap-fill me-2"),
                    html.H6("Functional Clustergram", className="d-inline-block m-0 fw-bold"),
                    html.I(
                        id="clustergram-help-icon",
                        className="bi bi-question-circle-fill text-muted ms-2",
                        style={'cursor': 'pointer', 'fontSize': '1rem'}
                    )
                ], className="d-flex align-items-center text-primary")
            ], className="bg-white border-bottom"),
            
            dbc.CardBody([
                clustergram_help_popover,
                dcc.Loading(html.Div(id='gprofiler-clustergram-output'), type="default")
            ])
        ], className="mb-4 shadow-sm border-0"),
        
    ], className="mt-2")

def create_reactome_layout(organism_options):
    """Layout for Reactome service with Standardized UI and Contextual Help"""
    
    reactome_options = [
        {'label': 'Project to Human', 'value': 'projection'},
        {'label': 'Include Disease', 'value': 'disease'},
        {'label': 'Include Interactors', 'value': 'interactors'}
    ]
    default_reactome_values = ['projection', 'disease']

    # --- Popover: Pathway Visualization Help ---
    pathway_vis_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Pathway Visualization Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("What is it?"),
                    html.Span(" An interactive diagram of the specific biological pathway selected in the table above.", className="small text-muted")
                ], className="mb-2"),
                html.Div([
                    html.Strong("How to use:"),
                    html.Ul([
                        html.Li("Select a row in the results table to load the diagram."),
                        html.Li("Click  to see details on Reactome.org."),
                    ], className="small text-muted ps-3 mb-0")
                ])
            ], style={'maxWidth': '350px'})
        ],
        id="reactome-vis-help-popover",
        target="reactome-vis-help-icon",
        trigger="legacy",
        placement="left",
    )

    # --- Popover: Fireworks Help ---
    fireworks_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Global Pathway Overview"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("The 'Fireworks' Plot:"),
                    html.Span(" A genome-wide view of all known pathways. Bright nodes represent pathways with significant enrichment from your list.", className="small text-muted")
                ], className="mb-2"),
                html.Div([
                    html.Strong("Navigation:"),
                    html.Ul([
                        html.Li("Zoom in to reveal sub-pathway hierarchies."),
                        html.Li("This view loads automatically after analysis."),
                    ], className="small text-muted ps-3 mb-0")
                ])
            ], style={'maxWidth': '350px'})
        ],
        id="fireworks-help-popover",
        target="fireworks-help-icon",
        trigger="legacy",
        placement="left",
    )

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
                            label="Standardize IDs (use g:Convert)",
                            value=True, 
                            className="d-inline-block fw-bold text-warning"
                        ),
                    ])
                ], width=12, md=5),

                # 3. Actions
                dbc.Col([
                    dbc.Label("Action", className="small text-uppercase text-muted fw-bold d-block"),
                    
                    html.Div([
                        # --- Icono Diagrama/Pathway con Spinner ---
                        html.Div(
                            dcc.Loading(
                                id="loading-reactome-spinner", 
                                type="circle", 
                                color="#ffc107", # Amarillo
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
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-diagram-3-fill me-2"),
                            html.H6("Reactome Pathway Visualization", className="d-inline-block m-0 fw-bold"),
                            
                            # Icono Ayuda Diagrama
                            html.I(
                                id="reactome-vis-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1rem'}
                            ),
                            
                            dcc.Loading(
                                id="loading-reactome-diagram-spinner", 
                                children=html.Div(id="reactome-diagram-spinner-output"), 
                                type="circle",
                                color="#ffc107"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"), 
                    
                    dbc.CardBody([
                        pathway_vis_help_popover, # Insertar Popover
                        html.Div(id='reactome-diagram-output', children=[
                            dbc.Alert("Select a pathway from the table above to visualize gene overlap.", color="light", className="text-center text-muted border-0")
                        ], className="p-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], width=12)
        ], className="g-4 mb-4 mt-2"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-stars me-2"),
                            html.H6("Global Pathway Overview (Fireworks)", className="d-inline-block m-0 fw-bold"),
                            
                            # Icono Ayuda Fireworks
                            html.I(
                                id="fireworks-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1rem'}
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"),
                    
                    dbc.CardBody([
                        fireworks_help_popover, # Insertar Popover
                        html.Div(id='reactome-fireworks-output', children=[
                            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="light", className="text-center text-muted border-0")
                        ], className="p-1")
                    ])
                ], className="h-100 shadow-sm border-0")
            ], width=12)
        ], className="g-4"),
        
        dcc.Store(id='reactome-scroll-fix-dummy', data=0)
    ], className="mt-2")    

def create_enrichment_tab_modified(): 
    """Main layout for Enrichment Tab with BioPareto Standard UI"""
    try:
        organism_options_gprofiler = get_organisms_from_api() 
    except Exception:
        organism_options_gprofiler = [{'label': 'Homo sapiens', 'value': 'hsapiens'}]
    organism_options_reactome = ReactomeService.get_reactome_organisms()
    
    # --- Popover: Main Guide ---
    main_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Enrichment Analysis Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("Goal:"),
                    html.Span(" Identify biological functions, pathways, and processes over-represented in your selected genes.", className="small text-muted")
                ], className="mb-2"),

                html.Div([
                    html.Strong("Workflow:"),
                    html.Ol([
                        html.Li("Select items from the Interest Panel (Left)."),
                        html.Li("Choose a service (g:Profiler or Reactome)."),
                        html.Li("Configure organism and ID settings."),
                        html.Li("Click 'Run Analysis'."),
                    ], className="small text-muted ps-3 mb-2")
                ]),
                
                html.Div([
                    html.Strong("Note:"), 
                    html.Span(" Multiple selections are automatically merged into a single unique gene list for analysis.", className="small text-danger")
                ], className="mb-0")
            ], style={'maxWidth': '350px'})
        ],
        id="enrichment-main-help-popover",
        target="enrichment-main-help-icon",
        trigger="legacy",
        placement="right",
    )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    # Header Estilizado
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-intersect me-2"),
                            html.H5("Biological Enrichment Analysis", className="d-inline-block m-0 fw-bold"),
                            
                            # Icono Ayuda Principal
                            html.I(
                                id="enrichment-main-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="Analysis guide"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),
                    
                    dbc.CardBody([
                        main_help_popover,
                        
                        html.P("Select one or more solutions or gene groups from the Interest Panel to analyze the functional enrichment of their genes.", className="text-muted small mb-4"),
                        
                        # --- Visual Selector Card ---
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="bi bi-check2-square me-2"),
                                "Selection Criteria"
                            ], className="small text-uppercase fw-bold bg-light text-dark"),
                            
                            dbc.CardBody([
                                html.Div(id='enrichment-visual-selector', children=[html.P("Loading items...", className="text-muted text-center py-4")]),
                                html.Div([
                                    dbc.Button([html.I(className="bi bi-trash3 me-2"), "Clear Selection"], id="clear-enrichment-selection-btn", color="danger", outline=True, size="sm", className="mt-2 shadow-sm"),
                                ], id="clear-enrichment-btn-container", style={'display': 'none'})
                            ])
                        ], className="mb-4 border shadow-sm"),
                        
                        html.Div(id='enrichment-selection-panel', className="mb-4"),
                        
                        # --- ALERT: No Selection (Visible by default if no selection) ---
                        dbc.Alert([
                            html.I(className="bi bi-arrow-up-circle me-2"),
                            "Please select at least one item from the selection panel above to start the analysis."
                        ], id="enrichment-empty-alert", color="info", className="d-flex align-items-center border-0 shadow-sm"),

                        # --- ANALYSIS MODULES (Hidden by default) ---
                        html.Div([
                            html.H5("Select Enrichment Service", className="mb-3 fw-bold text-dark"),
                            dbc.Tabs([
                                dbc.Tab(label="g:Profiler (GO, KEGG, REAC)", tab_id="gprofiler-tab", children=[create_gprofiler_layout(organism_options_gprofiler)], label_style={"fontWeight": "bold"}),
                                dbc.Tab(label="Reactome Pathways", tab_id="reactome-tab", children=[create_reactome_layout(organism_options_reactome)], label_style={"fontWeight": "bold"}),
                            ], id="enrichment-service-tabs", active_tab="gprofiler-tab", className="mb-3 nav-fill"),
                        ], id="enrichment-modules-wrapper", style={'display': 'none'})

                    ])
                ], className="shadow-sm border-0")
            ], width=12),
        ])
    ], fluid=True, className="py-3")