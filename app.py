# Pas# app.py (CÓDIGO COMPLETO CON CORRECCIÓN DE MODALES Y LÓGICA DE SET DE SOLUCIONES)

"""
BioPareto Analyzer - Aplicación Dash para análisis de frentes de Pareto en selección de genes
Desarrollado por Hugo Marciel - USACH 2025
"""

import os
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import base64
import io
import requests
from datetime import datetime
import logging
from io import BytesIO
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Importar matplotlib_venn si está disponible
try:
    from matplotlib_venn import venn2, venn3
except ImportError:
    pass 

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# 🔑 IMPORTACIONES DE LA NUEVA ARQUITECTURA MODULARIZADA 🔑
# -------------------------------------------------------------
# Servicios
from services.gprofiler_service import get_organisms_from_api 
# UI - Layouts de pestañas modulares
from ui.layouts.upload_tab import create_upload_tab
from ui.layouts.pareto_tab import create_pareto_tab
from ui.layouts.genes_tab import create_genes_tab
from ui.layouts.gene_groups_tab import create_gene_groups_tab
from ui.layouts.enrichment_tab import create_enrichment_tab_modified 
from ui.layouts.export_tab import create_export_tab 
# Lógica - Callbacks modulares
from logic.callbacks.data_management import register_data_management_callbacks
from logic.callbacks.pareto_plot import register_pareto_plot_callbacks
from logic.callbacks.pareto_selection import register_pareto_selection_callbacks
from logic.callbacks.consolidation import register_consolidation_callbacks
from logic.callbacks.genes_analysis import register_genes_analysis_callbacks
from logic.callbacks.gene_groups_analysis import register_gene_groups_callbacks
from logic.callbacks.enrichment_analysis import register_enrichment_callbacks
from logic.callbacks.export_callbacks import register_export_callbacks 
# -------------------------------------------------------------


# Inicialización de Dash y configuración
app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                suppress_callback_exceptions=True)

app.title = "BioPareto Analyzer"

# Estilos en el index_string se mantienen
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        /* ... Estilos CSS largos se mantienen aquí ... */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            padding: 30px;
        }
        /* ... Resto de estilos ... */
        .sticky-top {
            position: sticky;
            top: 20px; /* Adjust as needed */
            z-index: 1000;
        }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# -------------------------------------------------------------
# FUNCIONES DE LAYOUT Y AUXILIARES (SE MANTIENEN HASTA SU FASE)
# -------------------------------------------------------------

# create_navbar()
def create_navbar():
    """Create navigation bar with logos and title"""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Img(src="/assets/logo.png", height="60px", className="me-2") if True else None,
                            dbc.NavbarBrand("🧬 BioPareto Analyzer", className="ms-2", style={"fontSize": "2.0rem", "fontWeight": "bold"})
                        ],
                        width="auto"
                    ),
                    dbc.Col(
                        html.Img(src="/assets/LAI2B.png", height="40px"),
                        width="auto",
                        className="ms-auto"
                    )
                ],
                align="center",
                className="g-0 w-100"
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4"
    )

# create_interest_panel()
def create_interest_panel():
    """Create the interest panel/annotation board"""
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5("📌 Interest Panel", className="text-primary mb-0 d-inline-block"),
                dbc.Button(
                    "🗑️",
                    id="clear-interest-panel-btn",
                    color="link",
                    size="sm",
                    className="float-end",
                    title="Clear all items"
                )
            ])
        ]),
        dbc.CardBody([
            html.P("Save solutions, genes, and groups for later analysis",
                   className="text-muted small mb-3"),
            html.Div(id='interest-panel-content', children=[
                html.P("No items added yet", className="text-muted text-center py-4")
            ])
        ], style={'maxHeight': '600px', 'overflowY': 'auto'})
    ], className="sticky-top")

# Placeholder para la pestaña Export (A MOVER)
def create_export_tab():
    return html.Div("Export Tab (Loading...)")

# Funciones de reporte (A MOVER) - Se necesita mantener la estructura dummy para que compile el resto de callbacks
def create_pareto_plot_for_pdf(pareto_data):
    return BytesIO()
def create_genes_frequency_chart_for_pdf(pareto_data):
    return BytesIO()


# Layout principal (se mantiene aquí)
app.layout = dbc.Container([
    # STORES (se mantienen en app.py)
    dcc.Store(id='add-all-trigger-store', data=0), 
    dcc.Store(id='restore-trigger-store', data=0),
    dcc.Store(id='data-store', data={'fronts': [], 'fronts_history': [], 'main_objectives': None, 'explicit_objectives': []}),
    dcc.Store(id='enrichment-data-store'),
    dcc.Store(id='enrichment-params-store'),
    dcc.Store(id='objectives-store'),
    dcc.Store(id='interest-panel-store', data=[], storage_type='session'),
    dcc.Store(id='pareto-front-tab-temp-store', data=None),
    dcc.Store(id='genes-tab-gene-group-temp-store', data=None),
    dcc.Store(id='genes-tab-individual-gene-temp-store', data=None),
    dcc.Store(id='selected-solutions-store', data=[]),
    dcc.Store(id='combined-gene-groups-store', data=[], storage_type='session'),
    dcc.Store(id='gene-groups-analysis-tab-temp-store', data=None),
    dcc.Store(id='intersection-data-temp-store', data=None),
    dcc.Store(id='selected-gene-group-indices-store', data=[]), 
    dcc.Store(id='enrichment-selected-indices-store', data=[]),
    dcc.Store(id='pareto-layout-store', data={}), 
    dcc.Store(id='enrichment-selected-item-ids-store', data=[]), 
    
    # NUEVO TRIGGER STORE (PARA ESTABILIZAR ENRICHMENT)
    dcc.Store(id='enrichment-render-trigger-store', data=None), 


    # MODALES (se mantienen en app.py)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add to Interest Panel")),
        dbc.ModalBody([
            html.Div(id='pareto-front-tab-modal-item-info', className='mb-3'),
            dbc.Label("Add a comment or note:", className="fw-bold"),
            dbc.Textarea(
                id='pareto-front-tab-comment-input',
                placeholder="e.g., 'Promising solution', 'High accuracy set'...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="pareto-front-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Add to Panel", id="pareto-front-tab-confirm-btn", color="primary")
        ])
    ], id="pareto-front-tab-interest-modal", is_open=False),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add Genes to Interest Panel")),
        dbc.ModalBody([
            html.Div(id='genes-tab-modal-item-info', className='mb-3'),
            dbc.Label("Add a comment or note:", className="fw-bold"),
            dbc.Textarea(
                id='genes-tab-comment-input',
                placeholder="e.g., 'Key genes for analysis', 'High frequency gene group'...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="genes-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Add to Panel", id="genes-tab-confirm-btn", color="primary")
        ])
    ], id="genes-tab-interest-modal", is_open=False),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Create Combined Gene Group")),
        dbc.ModalBody([
            html.Div(id='gene-groups-analysis-tab-modal-info', className='mb-3'),
            dbc.Label("Group Name:", className="fw-bold"),
            dbc.Input(
                id='gene-groups-analysis-tab-name-input',
                placeholder="e.g., 'High-confidence genes from solutions 1-3'",
                type="text",
                className='mb-3'
            ),
            dbc.Label("Group Description/Comment:", className="fw-bold"),
            dbc.Textarea(
                id='gene-groups-analysis-tab-comment-input',
                placeholder="Describe the purpose or findings of this gene group...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="gene-groups-analysis-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Create Group", id="gene-groups-analysis-tab-confirm-btn", color="success")
        ])
    ], id="gene-groups-analysis-tab-modal", is_open=False),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirm Consolidation")),
        dbc.ModalBody([
            html.P(id='consolidate-modal-info', className='mb-3'),
            dbc.Label("New Front Name:", className="fw-bold"),
            dbc.Input(
                id='consolidate-front-name-input',
                placeholder="e.g., 'Consolidated Front 1'",
                type="text",
                className='mb-3'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="consolidate-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Consolidate", id="consolidate-confirm-btn", color="success")
        ])
    ], id="consolidate-modal", is_open=False),

    create_navbar(),

    html.Div([
        create_interest_panel()
    ], id="interest-panel-wrapper", style={
        'position': 'fixed',
        'right': '20px',
        'top': '120px',
        'width': '400px',
        'maxHeight': 'calc(100vh - 140px)',
        'overflowY': 'auto',
        'zIndex': '1000',
        'display': 'block'
    }),

    dbc.Container([
        dbc.Tabs([
            dbc.Tab(label="📁 Load Data", tab_id="upload-tab"),
            dbc.Tab(label="📊 Pareto Front", tab_id="pareto-tab"),
            dbc.Tab(label="🧬 Genes", tab_id="genes-tab"),
            dbc.Tab(label="🧬 Gene Groups Analysis", tab_id="gene-groups-tab"),
            dbc.Tab(label="🔬 Biological Analysis", tab_id="enrichment-tab"),
            dbc.Tab(label="📤 Export", tab_id="export-tab"),
        ], id="main-tabs", active_tab="upload-tab"),

        html.Div(id="tab-content", className="mt-4", style={'marginRight': '360px'})
    ], fluid=True),

    # Footer
    html.Footer([
        dbc.Container([
            html.Hr(),
            html.P("🧬 BioPareto Analyzer - Developed for gene selection analysis for Hugo Marciel's thesis project - USACH 2025",
                   className="text-center text-muted small")
        ])
    ])
], fluid=True, style={'marginBottom': '50px'})


# -------------------------------------------------------------
# CALLBACKS GENERALES DE UI (SE MANTIENEN HASTA SU FASE)
# -------------------------------------------------------------

# Callback auxiliar: Transfiere el clic del botón Add-All a un Store global (siempre visible).
@app.callback(
    Output('add-all-trigger-store', 'data', allow_duplicate=True),
    Input('add-to-interest-btn', 'n_clicks'),
    prevent_initial_call=True
)
def transfer_add_all_click(n_clicks):
    """Transfiere el n_clicks del botón real a un Store global."""
    if n_clicks is None:
        raise PreventUpdate
    return n_clicks

# 🔑 NUEVO CALLBACK DE ACTIVACIÓN (PARA ELIMINAR EL ERROR ESTRUCTURAL)
@app.callback(
    Output('enrichment-render-trigger-store', 'data', allow_duplicate=True),
    Input('main-tabs', 'active_tab'),
    prevent_initial_call=True
)
def trigger_enrichment_tab_render(active_tab):
    """Actualiza el trigger store SOLO cuando la pestaña de enriquecimiento está activa."""
    if active_tab == 'enrichment-tab':
        # Devolver un valor único (timestamp) para disparar el callback de renderizado
        return datetime.now().timestamp()
    # Si no es la pestaña correcta, no actualiza
    return dash.no_update 


# Callback para ocultar/mostrar panel de interés
@app.callback(
    Output("interest-panel-wrapper", "style"),
    Output("tab-content", "style"),
    Input("main-tabs", "active_tab")
)
def toggle_interest_panel_visibility(active_tab):
    """Ocultar el panel en pestañas de carga y exportación y ajustar el margen del contenido"""
    panel_style = {
        'position': 'fixed',
        'right': '20px',
        'top': '120px',
        'width': '400px',
        'maxHeight': 'calc(100vh - 140px)',
        'overflowY': 'auto',
        'zIndex': '1000'
    }

    if active_tab in ["upload-tab", "export-tab"]:
        panel_style['display'] = 'none'
        content_style = {'marginRight': '0px'}
    else:
        panel_style['display'] = 'block'
        content_style = {'marginRight': '440px'}

    return panel_style, content_style

# Callback para renderizar el contenido de la pestaña
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    """Render content based on active tab"""
    if active_tab == "upload-tab":
        return create_upload_tab()
    elif active_tab == "pareto-tab":
        return create_pareto_tab()
    elif active_tab == "genes-tab":
        return create_genes_tab()
    elif active_tab == "gene-groups-tab":
        return create_gene_groups_tab()
    elif active_tab == "enrichment-tab":
        # LLAMADA FINAL Y DEFINITIVA
        return create_enrichment_tab_modified() 
    elif active_tab == "export-tab":
        return create_export_tab()
    return html.Div("Tab not found")

# -------------------------------------------------------------
# CALLBACKS DE GESTIÓN DE INTERÉS Y MODALES (SE MANTIENEN HASTA SU FASE)
# -------------------------------------------------------------

@app.callback(
    [Output('pareto-front-tab-interest-modal', 'is_open'),
     Output('pareto-front-tab-modal-item-info', 'children'),
     Output('pareto-front-tab-comment-input', 'value'),
     Output('pareto-front-tab-temp-store', 'data'),
     Output('genes-tab-gene-group-temp-store', 'data', allow_duplicate=True),
     Output('genes-tab-individual-gene-temp-store', 'data', allow_duplicate=True)],
    [Input({'type': 'add-single-to-interest-btn', 'index': ALL}, 'n_clicks'),
     Input('pareto-front-tab-confirm-btn', 'n_clicks'),
     Input('pareto-front-tab-cancel-btn', 'n_clicks'),
     Input('add-all-trigger-store', 'data')],
    [State('selected-solutions-store', 'data'),
     State('pareto-front-tab-interest-modal', 'is_open'),
     State('pareto-front-tab-temp-store', 'data'),
     State({'type': 'add-single-to-interest-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def toggle_interest_modal(single_add_clicks, confirm_clicks, cancel_clicks, add_all_store_n_clicks,
                         selected_solutions, is_open, current_temp_store, single_btn_ids):
    """Toggle modal for adding items to interest panel (Pareto Front Tab) and performs cleanup."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    trigger_value = ctx.triggered[0]['value']

    if trigger_value is None or (isinstance(trigger_value, (int, float)) and trigger_value == 0 and trigger_id != 'add-all-trigger-store'):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Close modal on confirm or cancel (LIMPIEZA TOTAL)
    if trigger_id in ['pareto-front-tab-confirm-btn', 'pareto-front-tab-cancel-btn']:
        # 🔑 CORRECCIÓN: Cierra modal (False) y limpia stores temporales (None)
        return False, "", "", None, None, None

    # 1. Apertura por botón "Add All" (Conjunto)
    if trigger_id == 'add-all-trigger-store' and trigger_value > 0:
        if selected_solutions and len(selected_solutions) > 0:
            item_info = html.Div([
                html.P([
                    html.Strong("Adding Solution Set: "),
                    html.Span(f"{len(selected_solutions)} solutions")
                ]),
                html.P([
                    html.Strong("From: "),
                    html.Span(", ".join(set([sol['front_name'] for sol in selected_solutions])))
                ])
            ])
            return True, item_info, "", dash.no_update, None, None
        raise PreventUpdate

    # 2. Apertura por botón individual "📌" (Solución Individual)
    triggered_id_dict = ctx.triggered_id
    if triggered_id_dict and triggered_id_dict.get('type') == 'add-single-to-interest-btn':
        if single_add_clicks and any(c and c > 0 for c in single_add_clicks):
            clicked_index = triggered_id_dict['index']
            
            if selected_solutions:
                for sol in selected_solutions:
                    if sol['unique_id'] == clicked_index:
                        full_sol_data = sol['full_data'] 
                        
                        obj1_name = full_sol_data.get('objectives', [None])[0]
                        obj2_name = full_sol_data.get('objectives', [None, None])[1]
                        
                        obj1 = full_sol_data.get(obj1_name, 'N/A')
                        obj2 = full_sol_data.get(obj2_name, 'N/A')
                        
                        item_info = html.Div([
                            html.P([
                                html.Strong("Adding Solution: "),
                                html.Span(f"{full_sol_data['solution_id']} (from {sol['front_name']})")
                            ]),
                            html.P([
                                html.Strong("Key Values: "),
                                html.Span(f"{obj1_name.replace('_', ' ').title()}: {obj1}, {obj2_name.replace('_', ' ').title()}: {obj2}")
                            ])
                        ])
                        
                        return True, item_info, "", full_sol_data, None, None

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('pareto-front-tab-temp-store', 'data', allow_duplicate=True)],
    Input('pareto-front-tab-confirm-btn', 'n_clicks'),
    State('selected-solutions-store', 'data'),
    State('pareto-front-tab-temp-store', 'data'),
    State('pareto-front-tab-comment-input', 'value'),
    State('interest-panel-store', 'data'),
    State('data-store', 'data'),
    prevent_initial_call=True
)
def update_interest_panel_store_from_modal(confirm_clicks, selected_solutions, single_solution_data, comment, current_items, data_store):
    """Update interest panel store when modal confirmation occurs"""
    if not confirm_clicks:
        raise PreventUpdate

    if current_items is None:
        current_items = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    all_solutions_dict = {}
    if data_store:
        for front in data_store.get("fronts", []):
            for sol in front["data"]:
                all_solutions_dict[sol['solution_id']] = sol

    solutions_to_add = []
    is_single_solution = False

    if single_solution_data: 
        solutions_to_add.append(single_solution_data)
        is_single_solution = True
    elif selected_solutions and single_solution_data is None: 
        solutions_to_add = [sol['full_data'] for sol in selected_solutions]
    else:
        # 🔑 CORRECCIÓN: Si no hay data para guardar, limpia y aborta.
        return dash.no_update, None

    if not solutions_to_add:
        return dash.no_update, None
        
    final_solutions = []
    for sol in solutions_to_add:
        if 'front_name' not in sol:
            found_front_name = next((f['name'] for f in data_store.get('fronts', []) for s in f['data'] if s.get('solution_id') == sol.get('solution_id')), "Unknown Front")
            sol['front_name'] = found_front_name
        
        if 'unique_id' not in sol:
            sol['unique_id'] = f"{sol.get('solution_id', 'N/A')}|{sol['front_name']}"
            
        if 'selected_genes' not in sol:
            sol['selected_genes'] = all_solutions_dict.get(sol.get('solution_id'), {}).get('selected_genes', [])
            
        final_solutions.append(sol)
        

    if is_single_solution:
        sol = final_solutions[0]
        new_item = {
            'type': 'solution',
            'id': f"sol_{sol.get('solution_id', 'N/A')}_{timestamp}",
            'name': f"{sol.get('solution_id', 'N/A')} (from {sol.get('front_name', 'N/A')})",
            'comment': comment or "",
            'data': sol,
            'timestamp': timestamp
        }
        # 🔑 CORRECCIÓN: Limpia el Store Temporal (None) y devuelve el Store principal.
        return current_items + [new_item], None
    else:
        new_item = {
            'type': 'solution_set',
            'id': f"set_{len(current_items)}_{timestamp}",
            'name': f"Solution Set ({len(final_solutions)} solutions)",
            'comment': comment or "",
            'data': {'solutions': final_solutions},
            'timestamp': timestamp
        }
        # 🔑 CORRECCIÓN: Limpia el Store Temporal (None) y devuelve el Store principal.
        return current_items + [new_item], None

@app.callback(
    [Output('genes-tab-interest-modal', 'is_open', allow_duplicate=True),
     Output('genes-tab-modal-item-info', 'children', allow_duplicate=True),
     Output('genes-tab-comment-input', 'value', allow_duplicate=True),
     Output('genes-tab-gene-group-temp-store', 'data', allow_duplicate=True), 
     Output('pareto-front-tab-temp-store', 'data', allow_duplicate=True),
     Output('genes-tab-individual-gene-temp-store', 'data', allow_duplicate=True)],
    Input({'type': 'genes-tab-add-gene-group-btn', 'index': ALL}, 'n_clicks'), 
    [State('data-store', 'data')],
    prevent_initial_call=True
)
def open_modal_for_gene_groups(n_clicks_list, data):
    """Open modal when gene group buttons are clicked, setting context and cleaning others."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    triggered_item = ctx.triggered[0]
    if triggered_item['value'] is None or triggered_item['value'] == 0:
        raise PreventUpdate

    triggered_id_dict = ctx.triggered_id 
    if not triggered_id_dict or triggered_id_dict.get('type') != 'genes-tab-add-gene-group-btn':
        raise PreventUpdate
        
    clicked_index = triggered_id_dict['index']
    
    all_solutions_list = []
    for front in data.get("fronts", []):
        if front.get("visible", True):
            all_solutions_list.extend(front["data"])

    if not all_solutions_list:
        raise PreventUpdate

    all_genes = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
    gene_counts = pd.Series(all_genes).value_counts()
    total_solutions = len(all_solutions_list)

    if clicked_index == '100pct':
        genes_100_percent = gene_counts[gene_counts == total_solutions]
        if len(genes_100_percent) > 0:
            gene_list = sorted(genes_100_percent.index.tolist())

            item_info = html.Div([
                html.P([html.Strong("Adding Gene Group: "), html.Span("Genes Present in 100% of Solutions")]),
                html.P([html.Strong("Number of genes: "), html.Span(f"{len(gene_list)}")])
            ])
            default_comment = "Genes appearing in all solutions"

            gene_group_data = {
                'type': 'gene_set',
                'name': 'Genes Present in 100% of Solutions',
                'frequency': 100.0,
                'genes': gene_list,
                'count': len(gene_list)
            }
            return True, item_info, default_comment, gene_group_data, None, None
        else:
            raise PreventUpdate
    else: 
        try:
            clicked_percentage = float(clicked_index)
        except ValueError:
            raise PreventUpdate
            
        genes_at_percentage = []
        genes_under_100 = gene_counts[gene_counts < total_solutions]
        for gene, count in genes_under_100.items():
            percentage = round((count / total_solutions) * 100, 1)
            if percentage == clicked_percentage:
                genes_at_percentage.append(gene)

        if genes_at_percentage:
            gene_list = sorted(genes_at_percentage)
            item_info = html.Div([
                html.P([html.Strong("Adding Gene Group: "), html.Span(f"Genes with {clicked_percentage}% frequency")]),
                html.P([html.Strong("Number of genes: "), html.Span(f"{len(gene_list)}")])
            ])
            default_comment = f"Gene group at {clicked_percentage}% frequency"

            gene_group_data = {
                'type': 'gene_set',
                'name': f'Genes with {clicked_percentage}% frequency',
                'frequency': clicked_percentage,
                'genes': gene_list,
                'count': len(gene_list)
            }
            return True, item_info, default_comment, gene_group_data, None, None

    raise PreventUpdate

@app.callback(
    [Output('genes-tab-interest-modal', 'is_open', allow_duplicate=True),
     Output('genes-tab-modal-item-info', 'children', allow_duplicate=True),
     Output('genes-tab-comment-input', 'value', allow_duplicate=True),
     Output('genes-tab-individual-gene-temp-store', 'data', allow_duplicate=True),
     Output('pareto-front-tab-temp-store', 'data', allow_duplicate=True),
     Output('genes-tab-gene-group-temp-store', 'data', allow_duplicate=True)],
    Input({'type': 'add-gene-individual-btn', 'gene_name': ALL, 'source': ALL}, 'n_clicks'),
    State('genes-tab-interest-modal', 'is_open'),
    prevent_initial_call=True
)
def handle_genes_tab_individual_gene_button(n_clicks_list, is_open):
    """Handle individual gene button clicks in Genes tab, setting context and cleaning others."""
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    
    if triggered['value'] is None or triggered['value'] == 0:
        raise PreventUpdate

    triggered_id_dict = ctx.triggered_id
    
    if triggered_id_dict.get('type') != 'add-gene-individual-btn':
        raise PreventUpdate

    gene_name = triggered_id_dict.get('gene_name')
    source = triggered_id_dict.get('source')
    
    if gene_name is None or source is None:
        raise PreventUpdate

    if source == '100pct':
        source_display = "100% frequency genes"
    elif source.startswith('freq_'):
        try:
            source_percentage = source.split('_')[1]
            source_display = f"Frequency group {source_percentage}%"
        except IndexError:
            source_display = "Frequency group (Unknown %)"
    else:
        source_display = "Unknown source"

    modal_info = html.Div([
        html.P([html.Strong("Type: "), html.Span("🔬 Individual Gene", className="text-info")]),
        html.P([html.Strong("Gene: "), html.Code(gene_name, className="text-primary")]),
        html.P([html.Strong("Source: "), html.Span(source_display, className="text-muted")])
    ])

    default_comment = f"Individual gene {gene_name} from {source_display} analysis"

    temp_data = {
        'gene': gene_name,
        'source': source
    }

    return True, modal_info, default_comment, temp_data, None, None

# app.py (MODIFICACIÓN DE CALLBACK DE GESTIÓN DE MODALES DE GRUPOS DE GENES)

# ... (El resto del código de app.py se mantiene) ...

# app.py (FRAGMENTO DE CÓDIGO CORREGIDO PARA MODALES)

# ... (El resto del código de app.py se mantiene) ...

# app.py (FRAGMENTO MODIFICADO)

# ... (cerca del final del archivo, debajo de los callbacks de modales) ...

@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('gene-groups-analysis-tab-temp-store', 'data', allow_duplicate=True),
     Output('gene-groups-analysis-tab-modal', 'is_open', allow_duplicate=True),
     
     # Output('save-combined-group-btn-top', 'n_clicks', allow_duplicate=True)
     ], 
     
    [Input('gene-groups-analysis-tab-confirm-btn', 'n_clicks'),
     Input('gene-groups-analysis-tab-cancel-btn', 'n_clicks')],
    [State('gene-groups-analysis-tab-temp-store', 'data'),
     State('gene-groups-analysis-tab-name-input', 'value'),
     State('gene-groups-analysis-tab-comment-input', 'value'),
     State('interest-panel-store', 'data')],
    prevent_initial_call=True
)
def confirm_gene_group_addition(confirm_clicks, cancel_clicks, temp_data, group_name, group_comment, current_items):
    """Guarda el grupo combinado/intersección en el panel de interés y cierra el modal."""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 1. Manejo del Cancelar (Cierre del modal sin guardar)
    if trigger_id == 'gene-groups-analysis-tab-cancel-btn':
        # Esto permite que cada clic incremente naturalmente (1,2,3...) y Dash detecte el cambio
        return dash.no_update, dash.no_update, False

    # 2. Manejo del Confirmar (Guardar y Cierre)
    if trigger_id == 'gene-groups-analysis-tab-confirm-btn' and confirm_clicks:
        if not temp_data or not temp_data.get('genes'):
            return dash.no_update, None, False

        
        new_item = {
            'type': 'combined_gene_group',
            'id': f"group_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'name': group_name or "Unnamed Combined Group",
            'comment': group_comment or "",
            'data': {
                'genes': temp_data['genes'],
                'gene_count': len(temp_data['genes']),
                'source_items': temp_data['sources']
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if current_items is None:
            current_items = []

        return current_items + [new_item], None, False
        
    raise PreventUpdate

@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('genes-tab-gene-group-temp-store', 'data', allow_duplicate=True),
     Output('genes-tab-individual-gene-temp-store', 'data', allow_duplicate=True),
     Output('genes-tab-interest-modal', 'is_open', allow_duplicate=True),
     Output('genes-tab-modal-item-info', 'children', allow_duplicate=True),
     Output('genes-tab-comment-input', 'value', allow_duplicate=True)],
    [Input('genes-tab-confirm-btn', 'n_clicks'),
     Input('genes-tab-cancel-btn', 'n_clicks')],
    State('genes-tab-gene-group-temp-store', 'data'),
    State('genes-tab-individual-gene-temp-store', 'data'),
    State('genes-tab-comment-input', 'value'),
    State('interest-panel-store', 'data'),
    prevent_initial_call=True
)
def confirm_genes_tab_addition_to_panel(confirm_clicks, cancel_clicks, gene_group_data, individual_gene_data, comment, current_items):
    """Confirm and add genes to interest panel from Genes tab, and clear context."""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if current_items is None:
        current_items = []

    if trigger_id == 'genes-tab-cancel-btn':
        # 🔑 CORRECCIÓN MODAL: Cierra modal y limpia stores temporales.
        return dash.no_update, None, None, False, "", ""

    if trigger_id == 'genes-tab-confirm-btn':

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if gene_group_data:
            new_item = {
                'type': 'gene_set',
                'id': f"gene_set_{len(current_items)}_{timestamp}",
                'name': gene_group_data['name'],
                'comment': comment or gene_group_data.get('frequency', ''),
                'data': gene_group_data,
                'timestamp': timestamp
            }
            # Cierra modal, limpia stores temporales, y guarda item
            return current_items + [new_item], None, None, False, "", ""

        elif individual_gene_data:
            new_item = {
                'type': 'individual_gene',
                'id': f"gene_{individual_gene_data['gene']}_{timestamp}",
                'name': f"Gene: {individual_gene_data['gene']}",
                'comment': comment or f"Gene from {individual_gene_data['source']}",
                'data': individual_gene_data,
                'timestamp': timestamp
            }
            # Cierra modal, limpia stores temporales, y guarda item
            return current_items + [new_item], None, None, False, "", ""

    raise PreventUpdate

@app.callback(
    Output('interest-panel-content', 'children'),
    Input('interest-panel-store', 'data')
)
def render_interest_panel_content(items):
    """Render the visual content of the interest panel based on stored items"""
    if not items or len(items) == 0:
        return html.P("No items added yet", className="text-muted text-center py-4")

    panel_items = []
    for idx, item in enumerate(items):
        item_type = item.get('type', 'unknown')
        item_name = item.get('name', 'Unknown Item')
        item_comment = item.get('comment', '')
        item_timestamp = item.get('timestamp', '')

        if item_type == 'solution':
            badge = dbc.Badge("Solution", color="primary", className="me-2")
        elif item_type == 'solution_set':
            badge = dbc.Badge("Solution Set", color="info", className="me-2")
        elif item_type == 'gene_set':
            badge = dbc.Badge("Gene Group", color="success", className="me-2")
        elif item_type == 'individual_gene':
            badge = dbc.Badge("Gene", color="warning", className="me-2")
        elif item_type == 'combined_gene_group':
            badge = dbc.Badge("Combined Group", color="success", className="me-2")
        else:
            badge = dbc.Badge("Unknown", color="secondary", className="me-2")

        extra_info = ""
        if item_type == 'combined_gene_group':
            gene_count = item.get('data', {}).get('gene_count', 0)
            source_count = len(item.get('data', {}).get('source_items', []))
            extra_info = html.Div([
                html.P(f"Genes: {gene_count} | Sources: {source_count}",
                       className="small text-muted mb-1")
            ])

        item_card = dbc.Card([
            dbc.CardBody([
                html.Div([
                    badge,
                    html.Strong(item_name, className="d-inline-block"),
                    dbc.Button(
                        "×",
                        id={'type': 'remove-interest-item', 'index': idx},
                        color="link",
                        size="sm",
                        className="float-end text-danger p-0",
                        style={'fontSize': '1.5rem', 'lineHeight': '1'}
                    )
                ], className="mb-2"),
                extra_info,
                html.P(item_comment, className="small text-muted mb-1") if item_comment else None,
                html.P(f"Added: {item_timestamp}", className="small text-muted mb-0")
            ])
        ], className="mb-2")

        panel_items.append(item_card)

    return panel_items

@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
     Output('selected-gene-group-indices-store', 'data', allow_duplicate=True)],
    Input('clear-interest-panel-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_interest_panel(n_clicks):
    """Clear all items from the interest panel and clear selection stores"""
    return [], [], []

@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
     Output('selected-gene-group-indices-store', 'data', allow_duplicate=True)],
    Input({'type': 'remove-interest-item', 'index': ALL}, 'n_clicks'),
    State('interest-panel-store', 'data'),
    State('enrichment-selected-indices-store', 'data'),
    State('selected-gene-group-indices-store', 'data'),
    prevent_initial_call=True
)
def remove_individual_interest_panel_item(n_clicks_list, current_items, current_enrich_indices, current_group_indices):
    """Remove individual item from interest panel when × button is clicked, and update selection indices."""
    ctx = dash.callback_context

    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id = json.loads(triggered_id)
    index_to_remove = button_id['index']

    if current_items and 0 <= index_to_remove < len(current_items):
        updated_items = current_items[:index_to_remove] + current_items[index_to_remove + 1:]
        
        def adjust_indices(indices, removed_index):
            return [idx if idx < removed_index else idx - 1 for idx in indices if idx != removed_index]

        new_enrich_indices = adjust_indices(current_enrich_indices, index_to_remove)
        new_group_indices = adjust_indices(current_group_indices, index_to_remove)
        
        new_enrich_indices = [idx for idx in new_enrich_indices if 0 <= idx < len(updated_items)]
        new_group_indices = [idx for idx in new_group_indices if 0 <= idx < len(updated_items)]

        return updated_items, new_enrich_indices, new_group_indices

    raise PreventUpdate

@app.callback(
    Output('gene-groups-selector', 'options'),
    Input('interest-panel-store', 'data')
)
def update_gene_groups_selector(items):
    """Update the gene groups selector with available items from interest panel"""
    if not items:
        return []

    options = []
    for idx, item in enumerate(items):
        item_type = item.get('type', '')
        item_name = item.get('name', '')

        if item_type in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
            options.append({
                'label': f"{item_name} ({item_type})",
                'value': idx
            })

    return options


# ------------------------------------------------------------
# Lógica de Modales de Selección de Soluciones (Pareto Front)
# ------------------------------------------------------------
@app.callback(
    [Output('interest-panel-store', 'data', allow_duplicate=True),
     Output('pareto-selection-temp-store', 'data', allow_duplicate=True), # Limpia el Store Temporal
     Output('pareto-selection-modal', 'is_open', allow_duplicate=True)], # Cierra el Modal
    [Input('pareto-selection-confirm-btn', 'n_clicks'),
     Input('pareto-selection-cancel-btn', 'n_clicks')], 
    [State('pareto-selection-temp-store', 'data'),
     State('pareto-selection-name-input', 'value'),
     State('pareto-selection-comment-input', 'value'),
     State('interest-panel-store', 'data')], # Store Principal
    prevent_initial_call=True
)
def confirm_pareto_selection_addition(confirm_clicks, cancel_clicks, temp_data, group_name, group_comment, current_items):
    """Guarda la solución/conjunto de soluciones en el panel de interés y cierra el modal."""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 1. Manejo del Cancelar (Cierre del modal sin guardar)
    if trigger_id == 'pareto-selection-cancel-btn':
        # 🔑 CORRECCIÓN: Cierra modal (False) y limpia stores temporales (None)
        return dash.no_update, None, False 

    # 2. Manejo del Confirmar (Guardar y Cierre)
    if trigger_id == 'pareto-selection-confirm-btn' and confirm_clicks:
        if not temp_data or not temp_data.get('genes'): # Validar que haya datos
            # Cierra si no hay data válida
            return dash.no_update, None, False 
        
        # Determinar el tipo de ítem a guardar
        item_type = temp_data.get('type', 'solution') # Puede ser 'solution' o 'solution_set'
        name_default = "Unnamed Set" if item_type == 'solution_set' else f"Solution {temp_data.get('id', 'N/A')}"
            
        new_item = {
            'type': item_type,
            # ID único para el Panel de Interés (distinto al id de la solución/front)
            'id': f"item_{datetime.now().strftime('%Y%m%d%H%M%S')}_{item_type}", 
            'name': group_name or name_default,
            'comment': group_comment or "",
            'data': temp_data, # Guardamos el objeto temp_data completo
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if current_items is None:
            current_items = []

        # 🔑 CORRECCIÓN: Retorna el store actualizado, resetea temp_store (None), y cierra el modal (False)
        return current_items + [new_item], None, False
        
    raise PreventUpdate


if __name__ == '__main__':
    print("🚀 Iniciando BioPareto Analyzer...")
    print("--------------------------------------------------")

    # 🔑 REGISTRO DE CALLBACKS MODULARIZADOS 🔑
    register_data_management_callbacks(app)
    register_pareto_plot_callbacks(app)
    register_pareto_selection_callbacks(app)
    register_consolidation_callbacks(app)
    register_genes_analysis_callbacks(app)
    register_gene_groups_callbacks(app)
    
    # 🔑 REGISTROS DE LA FASE 4 (CORREGIDOS PARA NOMBRES FINALES)
    from logic.callbacks.enrichment_analysis import register_enrichment_callbacks
    register_enrichment_callbacks(app) 
    from logic.callbacks.export_callbacks import register_export_callbacks
    register_export_callbacks(app)

    print("✅ Módulos de Load Data (upload-tab) registrados.")
    print("✅ Módulos de Pareto Front (pareto-tab) registrados.")
    print("✅ Módulos de Genes y Grupos (genes-tab) registrados.")
    print("✅ Módulos de Análisis Biológico y Exportación registrados.")
    print("--------------------------------------------------")
    print("🌐 Accede a la aplicación en: http://127.0.0.1:8050/")

    port = int(os.environ.get("PORT", 80))
    app.run(debug=True, host='0.0.0.0', port=port)