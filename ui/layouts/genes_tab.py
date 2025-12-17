# ui/layouts/genes_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc 

def create_genes_tab():
    """
    Create selected genes tab layout with In-Place Expansion (Accordion Style)
    and Contextual Help for both Frequency and Explorer sections.
    """
    
    # --- 1. Popover de Ayuda: Gene Frequency Overview (ESTILO REFERENCIA) ---
    frequency_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Gene Frequency Guide"),
            dbc.PopoverBody([
                # Concepto
                html.Div([
                    html.Strong("Concept:"), 
                    html.Span(" Analyzes gene stability (consensus) across all selected solutions. High-frequency genes are considered more robust biomarkers.", className="small text-muted")
                ], className="mb-2"),

                # 100% Conserved
                html.Div([
                    html.Strong("🎯 100% Conserved:"),
                    html.Span(" The top panel highlights genes present in ", className="small text-muted"),
                    html.Em("every single solution", className="small fw-bold text-dark"),
                    html.Span(". These are your strongest candidates.", className="small text-muted")
                ], className="mb-2"),

                # Frequency Chart
                html.Div([
                    html.Strong("📊 Frequency Chart:"),
                    html.Span(" Shows the distribution of the remaining genes.", className="small text-muted"),
                    html.Div([
                        html.Div("• Right side (High %): Genes/Probes appearing in most solutions.", className="small text-muted ps-2"),
                        html.Div("• Left side (Low %): Genes/Probes specific to fewer solutions.", className="small text-muted ps-2")
                    ], className="mt-1")
                ], className="mb-2"),

                # Interaction
                html.Div([
                    html.Strong("🖱️ Interaction:"),
                    html.Span(" Click any blue bar to ", className="small text-muted"),
                    html.Strong("expand the detailed gene list", className="small text-primary"),
                    html.Span(" below for that specific frequency group.", className="small text-muted")
                ], className="mb-0")
            ])
        ],
        id="freq-section-help-popover",
        target="freq-help-icon",
        trigger="legacy",
        placement="right",
        style={'maxWidth': '350px'}
    )

    # --- 2. Popover de Ayuda: Explorer Guide & Metrics (ESTILO UNIFICADO) ---
    explorer_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Explorer Guide & Metrics"),
            dbc.PopoverBody([
                
                # Paso 1: Selección
                html.Div([
                    html.Strong("1. Select Data:"), 
                    html.Span(" Choose a Front and a Metric to analyze. Common examples include:", className="small text-muted"),
                    
                    # Sub-bloque para métricas (indentado con borde sutil)
                    html.Div([
                        html.Div([
                            html.Code("Optimization Objectives", className="text-dark fw-bold"),
                            html.Span(" (e.g., 1-Auc): ", className="small text-muted"),
                            html.Strong("Performance Metric.", className="small text-dark"),
                            html.Div("Use the histogram to identify the cluster of best-performing solutions. Clicking a bar selects all solutions in that range.", className="small text-muted mt-1")
                        ], className="mb-2"),

                        html.Div([
                            html.Code("Complexity Metrics", className="text-dark fw-bold"),
                            html.Span(" (e.g., Gene Ratio): ", className="small text-muted"),
                            html.Strong("Model Parsimony.", className="small text-dark"),
                            html.Div("Represents the size of the solution. Lower values imply fewer genes. Crucial for cost-effective validation.", className="small text-muted mt-1")
                        ], className="mb-2"),

                        html.Div([
                            html.Code("Gene", className="text-dark fw-bold"),
                            html.Span(": ", className="small text-muted"),
                            html.Strong("Consensus Ranking.", className="small text-dark"),
                            html.Div("Ranks genes by frequency within filtered rows. Answer: 'Which genes dominate high-accuracy solutions?'.", className="small text-muted mt-1"),
                            html.Div([html.I(className="bi bi-cursor-fill me-1"), "Click any gene bar to save to panel."], className="small text-primary mt-1")
                        ], className="mb-0")
                    ], className="ps-3 border-start border-2 mt-2 mb-2")
                ], className="mb-2"),
                
                # Paso 2: Refinar
                html.Div([
                    html.Strong("2. Refine:"), 
                    html.Span(" Type in the table headers (e.g., ", className="small text-muted"),
                    html.Code("< 0.05", className="small"),
                    html.Span(") to filter specific solutions.", className="small text-muted")
                ], className="mb-2"),
                
                # Paso 3: Analizar
                html.Div([
                    html.Strong("3. Analyze:"), 
                    html.Span(" The Histogram updates automatically to show the data distribution of the filtered rows.", className="small text-muted")
                ], className="mb-2"),
                
                # Paso 4: Guardar
                html.Div([
                    html.Strong("4. Save:"), 
                    html.Span(" Use 'Save Visible' to capture the resulting gene set.", className="small text-muted")
                ], className="mb-0")

            ], style={'maxWidth': '400px'}), 
        ],
        id="explorer-section-help-popover",
        target="explorer-help-icon",
        trigger="legacy",
        placement="left",
    )

    return dbc.Container([
        
        # --- SECCIÓN 1: GLOBAL OVERVIEW ---
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-bar-chart-line-fill me-2"),
                            html.H5("Gene Frequency Overview", className="d-inline-block m-0 fw-bold"),
                            html.I(
                                id="freq-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="Click for frequency guide"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),
                    
                    dbc.CardBody([
                        frequency_help_popover,
                        html.P("Overview of genes identified across all selected solutions. Click a bar to view detailed gene list below.", 
                               className="text-muted small mb-4"),
                        html.Div(id="common-genes-analysis") 
                    ])
                ], className="shadow-sm border-0 mb-4")
            ], width=12),
        ]),
        
        # --- SECCIÓN 2: DETAILED EXPLORER ---
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-table me-2"),
                            html.H5("Solution Explorer & Data Table", className="d-inline-block m-0 fw-bold"),
                            html.I(
                                id="explorer-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="Click for metrics guide"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),
                    
                    dbc.CardBody([
                        explorer_help_popover,
                        html.P("Interactive exploration of specific solutions and gene metrics. Use the controls below to filter data.", 
                               className="text-muted small mb-3"),
                        html.Div(id="genes-table-container")
                    ])
                ], className="shadow-sm border-0")
            ], width=12),
        ]),
        
        # --- STORES Y MODALES ---
        dcc.Store(id='genes-analysis-internal-store'),
        dcc.Store(id='genes-graph-temp-store'),

        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id='genes-graph-modal-title')),
                dbc.ModalBody(id='genes-graph-modal-body'),
                dbc.ModalFooter(id='genes-graph-modal-footer'),
            ],
            id='genes-graph-action-modal',
            is_open=False,
            centered=True,
        )
        
    ], fluid=True, className="py-3")
