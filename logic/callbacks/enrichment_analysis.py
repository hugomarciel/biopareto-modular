# logic/callbacks/enrichment_analysis.py

"""
Módulo de Callbacks para la Pestaña de Análisis de Enriquecimiento.
"""

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table, MATCH # <--- MATCH agregado
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import logging
import numpy as np
import math 
import plotly.express as px
import plotly.graph_objects as go
from services.gprofiler_service import GProfilerService 
from services.reactome_service import ReactomeService 
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist, squareform

logger = logging.getLogger(__name__)

# --- FUNCIÓN DE MANHATTAN PLOT ---

# Reemplaza la función 'create_gprofiler_manhattan_plot' con esta versión actualizada (Zig-Zag):

# Reemplaza la función 'create_gprofiler_manhattan_plot' con esta versión (Rotación -45°):

def create_gprofiler_manhattan_plot(df, threshold_value):
    line_threshold_value = 0.05 
    try:
        float_threshold = float(threshold_value)
        if 0 < float_threshold <= 1.0:
            line_threshold_value = float_threshold
    except (TypeError, ValueError):
        pass
    
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant terms to display in the Manhattan Plot.", xaxis={'visible': False}, yaxis={'visible': False}, height=400)
        return fig
        
    df['-log10(P-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    
    all_sources = df['source'].unique()
    go_sources = sorted([s for s in all_sources if s.startswith('GO:')])
    other_sources = sorted([s for s in all_sources if not s.startswith('GO:')])
    source_order = go_sources + other_sources

    df['source'] = pd.Categorical(df['source'], categories=source_order, ordered=True)
    df = df.sort_values(['source', 'p_value'], ascending=True)
    df['term_index'] = df.groupby('source', observed=True).cumcount() + 1
    
    y_threshold = -np.log10(line_threshold_value)
    line_name = f"Gold Standard Threshold (P < {line_threshold_value:.4f})" 
    
    df['is_gold_standard'] = df['-log10(P-value)'] >= y_threshold
    df['plot_color_group'] = df.apply(lambda row: 'Gold' if row['is_gold_standard'] else row['source'], axis=1)
    
    source_colors = px.colors.qualitative.Bold
    source_color_map = {source: source_colors[i % len(source_colors)] for i, source in enumerate(df['source'].unique())}
    color_map = {'Gold': 'red'} 
    for source, color in source_color_map.items():
        color_map[source] = color 

    min_size = 5
    max_size = 40 
    max_val = df['intersection_size'].max()
    
    if max_val == 0:
        df['marker_size'] = min_size
    else:
        df['marker_size'] = (df['intersection_size'].clip(lower=0) * (max_size - min_size) / max_val) + min_size
        
    df['marker_size'] = df['marker_size'].clip(upper=max_size)
    
    df_plot = df.copy().reset_index(drop=True)

    if df_plot.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant terms found to plot.", xaxis={'visible': False}, yaxis={'visible': False}, height=400)
        return fig
    
    fig = px.scatter(
        df_plot, 
        x='term_index',                     
        y='-log10(P-value)',                
        color='plot_color_group',           
        color_discrete_map=color_map,       
        size='marker_size',                 
        custom_data=['term_name', 'p_value', 'intersection_size', 'source', 'is_gold_standard'],
        hover_data={'term_index': False, '-log10(P-value)': ':.2f', 'term_name': True, 'p_value': ':.2e', 'intersection_size': True, 'source': True, 'is_gold_standard': True}
    )
    
    # Calcular centros de etiquetas
    source_labels = df_plot.groupby('source', observed=True)['term_index'].agg(['min', 'max']).reset_index() 
    source_labels['center'] = (source_labels['min'] + source_labels['max']) / 2
    
    # --- CAMBIO: Rotación -45 grados (Más robusto que Zig-Zag) ---
    # Usamos directamente las fuentes originales, sin saltos de línea <br>
    
    fig.update_layout(
        xaxis={
            'title': "Functional Enrichment Terms (Grouped by Source)", 
            'tickmode': 'array', 
            'tickvals': source_labels['center'], 
            'ticktext': source_labels['source'], # Usamos el texto limpio
            'showgrid': False, 
            'zeroline': False, 
            'tickangle': -45  # <--- ROTACIÓN APLICADA AQUÍ
        },
        yaxis={'title': '-log10(P-value)', 'automargin': True},
        showlegend=True,
        height=550,
        # Aumentamos el margen inferior ('b') para dar espacio al texto rotado
        margin={'t': 30, 'b': 120, 'l': 50, 'r': 10}, 
        plot_bgcolor='white',
        dragmode='pan',      
        hovermode='closest'  
    )

    fig.add_hline(y=y_threshold, line_dash="dot", line_color="red", annotation_text=line_name, annotation_position="top right")

    fig.update_traces(
        marker=dict(opacity=0.6, line=dict(width=0.5, color='DarkSlateGrey')),
        hovertemplate="<b>Term:</b> %{customdata[0]}<br><b>Source:</b> %{customdata[3]}<br><b>-log10(P-value):</b> %{y:.2f}<br><b>P-value:</b> %{customdata[1]:.2e}<br><b>Genes Matched:</b> %{customdata[2]}<br><b>Gold Standard:</b> %{customdata[4]}<br><extra></extra>"
    )

    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True,
        showspikes=True, 
        spikethickness=1, 
        spikedash='dot', 
        spikemode='across', 
        spikecolor='#888888'
    )
    
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True,
        showspikes=True, 
        spikethickness=1, 
        spikedash='dot', 
        spikemode='across',
        spikecolor='#888888'
    )
    
    return fig
# --- FUNCIÓN DE HEATMAP ---
def process_data_for_gene_term_heatmap(stored_data, threshold=0.05, max_terms=50):
    results = stored_data.get('results', [])
    gene_list_validated = stored_data.get('gene_list_validated', []) 
    
    debug_counters = {
        'timestamp_start': datetime.now().strftime("%H:%M:%S.%f"), 'initial_terms': len(results), 'initial_genes': len(gene_list_validated), 'terms_after_pvalue_filter': 0,
        'terms_before_zerovariance_clean': 0, 'genes_before_zerovariance_clean': 0, 'terms_removed_by_zerovariance': 0, 'genes_removed_by_zerovariance': 0, 'timestamp_end': None
    }
    
    if not results or not gene_list_validated:
        return pd.DataFrame(), debug_counters

    df = pd.DataFrame(results)

    if df.empty:
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    df['-log10(q-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    df_significant = df[df['p_value'] < threshold].sort_values(by='p_value', ascending=True).head(max_terms) 
    
    debug_counters['terms_after_pvalue_filter'] = len(df_significant)
    
    if df_significant.empty:
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    term_list = df_significant['term_name'].tolist()
    heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_validated)
    
    for _, row in df_significant.iterrows():
        term_name = row['term_name']
        log_q_value = row['-log10(q-value)'] 
        raw_intersecting_genes = row.get('intersection_genes', [])
        
        for gene in raw_intersecting_genes:
            if gene in gene_list_validated:
                heatmap_matrix.loc[term_name, gene] = log_q_value
                
    debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    return heatmap_matrix, debug_counters


def create_gene_term_heatmap(heatmap_matrix):
    if heatmap_matrix.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant gene-term associations remain after filtering.", height=400)
        return fig
    
    perform_row_clustering = heatmap_matrix.shape[0] >= 2
    perform_col_clustering = heatmap_matrix.shape[1] >= 2
    
    clustered_matrix = heatmap_matrix.copy()
    clustering_successful = True
    
    try:
        if perform_row_clustering:
            row_linkage = sch.linkage(pdist(clustered_matrix, metric='correlation'), method='average')
            row_order_indices = sch.dendrogram(row_linkage, orientation='right', no_plot=True)['leaves']
            clustered_matrix = clustered_matrix.iloc[row_order_indices, :]
        
        if perform_col_clustering:
            col_linkage = sch.linkage(pdist(clustered_matrix.T, metric='correlation'), method='average')
            col_order_indices = sch.dendrogram(col_linkage, orientation='top', no_plot=True)['leaves']
            clustered_matrix = clustered_matrix.iloc[:, col_order_indices]
            
    except ValueError as e:
        logger.error(f"Clustering failed: {e}. Plotting without clustering.")
        clustered_matrix = heatmap_matrix.copy()
        clustering_successful = False

    z_max = clustered_matrix.values.max()
    z_min = 0.0 
    colormap = px.colors.sequential.Plasma
    member_matrix = np.where(clustered_matrix.values > 0, "Sí", "No")
    
    fig = go.Figure(data=go.Heatmap(
        z=clustered_matrix.values,        
        x=clustered_matrix.columns,       
        y=clustered_matrix.index,         
        colorscale=colormap,
        zmin=z_min,
        zmax=z_max,
        showscale=True,
        colorbar=dict(title=dict(text='-log10(q-value)', side='right'), thickness=15, len=0.7),
        customdata=member_matrix,         
        hovertemplate="<b>Term:</b> %{y}<br><b>Gene:</b> %{x}<br><b>-log10(p-value):</b> %{z:.2f}<br><b>Membresía:</b> %{customdata} <br><extra></extra>"
    ))

    status_parts = []
    if clustering_successful and perform_row_clustering and perform_col_clustering:
        status_parts.append("Clustered Successfully")
    else:
        status_parts.append("Not Clustered")
    if not perform_row_clustering or not perform_col_clustering:
         status_parts.append("(Low Dimension)")
    clustering_status = " ".join(status_parts)

    fig.update_layout(
        title=f"Functional Clustergram (Term vs. Gene Membership) - {clustering_status}",
        xaxis_title="Genes de Entrada",
        yaxis_title="Términos Enriquecidos",
        xaxis={'tickangle': 90, 'showgrid': False, 'zeroline': False},
        yaxis={'showgrid': False, 'zeroline': False, 'automargin': True},
        height=min(max(50 * clustered_matrix.shape[0], 500), 1000),
        margin=dict(l=250, r=20, t=50, b=100) 
    )
    return fig


# --- REGISTRO DE CALLBACKS ---
def register_enrichment_callbacks(app): 
    """
    Registra todos los callbacks de la pestaña de enriquecimiento en la app principal.
    """
    
    # --- NUEVO: CLIENTSIDE CALLBACK PARA FEEDBACK VISUAL INSTANTÁNEO (Estilo Tarjeta) ---
    # Esto cambia el borde y fondo de la tarjeta inmediatamente al hacer clic
    app.clientside_callback(
        """
        function(selected_value) {
            // selected_value es una lista. Si tiene elementos, está seleccionado.
            const is_selected = selected_value && selected_value.length > 0;
            
            if (is_selected) {
                return [
                    {
                        'transition': 'all 0.2s ease-in-out',
                        'border': '2px solid #0d6efd',       // Borde Azul Fuerte
                        'backgroundColor': '#f0f8ff',        // Fondo Azul Pálido
                        'transform': 'scale(1.02)',          // Efecto Pop sutil
                        'cursor': 'pointer'
                    },
                    "h-100 shadow" // Clase con sombra más fuerte
                ];
            } else {
                return [
                    {
                        'transition': 'all 0.2s ease-in-out',
                        'border': '1px solid rgba(0,0,0,0.125)', // Borde default
                        'backgroundColor': 'white',
                        'transform': 'scale(1)',
                        'cursor': 'pointer'
                    },
                    "h-100 shadow-sm hover-shadow" // Clase normal
                ];
            }
        }
        """,
        [Output({'type': 'enrichment-card-wrapper', 'index': MATCH}, 'style'),
         Output({'type': 'enrichment-card-wrapper', 'index': MATCH}, 'className')],
        Input({'type': 'enrichment-card-checkbox', 'index': MATCH}, 'value'),
        prevent_initial_call=True
    )
    # ---------------------------------------------------------------------------

    # --- NUEVOS CALLBACKS UI: Deshabilitar selectores si no hay validación ---
    @app.callback(
        Output('gprofiler-target-namespace', 'disabled'),
        Input('gprofiler-validation-switch', 'value')
    )
    def toggle_gprofiler_namespace_state(use_validation):
        return not use_validation

    @app.callback(
        Output('reactome-target-namespace', 'disabled'),
        Input('reactome-validation-switch', 'value')
    )
    def toggle_reactome_namespace_state(use_validation):
        return not use_validation
    # ---------------------------------------------------------------------------

    # 1. Callback de Actualización de IDs y Trigger
    @app.callback(
        [Output('enrichment-selected-item-ids-store', 'data', allow_duplicate=True),
         Output('enrichment-render-trigger-store', 'data', allow_duplicate=True)],
        [Input('interest-panel-store', 'data'),
         Input('enrichment-selected-indices-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=True 
    )
    def update_selected_items_and_render_trigger(items, selected_indices_list, active_tab):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id in ['interest-panel-store', 'enrichment-selected-indices-store'] or (trigger_id == 'main-tabs' and active_tab == 'enrichment-tab'):
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        raise PreventUpdate


    # 1.5. Callback de Renderizado Visual (ESTILO REPLICADO DE GGA)
    @app.callback(
        Output('enrichment-visual-selector', 'children'),
        Input('enrichment-render-trigger-store', 'data'), 
        [State('interest-panel-store', 'data'),
         State('enrichment-selected-indices-store', 'data'),
         State('main-tabs', 'active_tab'),
         State('data-store', 'data')]
    )
    def render_visual_enrichment_selector(trigger_data, items, selected_indices_list, active_tab, data_store):
        """
        Render visual card-based selector matching the Interest Panel standard exactly like Gene Groups Tab.
        """
        if active_tab != 'enrichment-tab':
             raise PreventUpdate 

        if not items:
            return html.P("No items available. Add solutions, genes, or gene groups to your Interest Panel first.",
                         className="text-muted text-center py-4")

        if selected_indices_list is None:
            selected_indices_list = []

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', 'Unknown')
            item_comment = item.get('comment', '')
            item_origin = item.get('tool_origin', 'Manual Selection')
            data = item.get('data', {})

            # Filtrar tipos válidos
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            # --- LÓGICA DE ESTANDARIZACIÓN (IDÉNTICA A GGA / APP.PY) ---
            # 1. Definir Estilos
            if item_type == 'solution':
                badge_color, icon, badge_text = "primary", "🔵", "Solution"
            elif item_type == 'solution_set':
                badge_color, icon, badge_text = "info", "📦", "Set"
            elif item_type == 'gene_set':
                badge_color, icon, badge_text = "success", "🧬", "Gene Group"
            elif item_type == 'individual_gene':
                badge_color, icon, badge_text = "warning", "🔬", "Gene"
            elif item_type == 'combined_gene_group':
                badge_color, icon, badge_text = "success", "🎯", "Combined"
            else:
                badge_color, icon, badge_text = "secondary", "❓", "Unknown"

            # 2. Definir Línea Estadística (Genes | Contexto)
            stats_text_left = ""
            stats_text_right = ""

            if item_type == 'solution':
                genes = data.get('selected_genes', [])
                # Si faltan genes en el item, intentar buscarlos en el data_store general (fallback)
                if not genes and data_store:
                    # Lógica de recuperación auxiliar (opcional pero recomendada)
                    pass 
                
                stats_text_left = f"Genes: {len(genes)}"
                stats_text_right = f"Source: {data.get('front_name', 'Front?')}"
                
            elif item_type == 'solution_set':
                # Soporte robusto para items antiguos y nuevos
                n_genes = data.get('unique_genes_count', 0)
                if n_genes == 0 and 'solutions' in data:
                     unique_g = set()
                     for s in data['solutions']: unique_g.update(s.get('selected_genes', []))
                     n_genes = len(unique_g)
                
                stats_text_left = f"Genes: {n_genes}"
                stats_text_right = f"Solutions: {len(data.get('solutions', []))}"

            elif item_type == 'gene_set':
                stats_text_left = f"Genes: {len(data.get('genes', []))}"
                freq = data.get('frequency')
                stats_text_right = f"Freq: {freq}%" if freq else "Source: Table"

            elif item_type == 'individual_gene':
                stats_text_left = f"ID: {data.get('gene')}"
                stats_text_right = f"Src: {data.get('source', 'Unknown')}"

            elif item_type == 'combined_gene_group':
                stats_text_left = f"Genes: {data.get('gene_count', 0)}"
                stats_text_right = f"Sources: {len(data.get('source_items', []))}"

            # 3. Estado de Selección
            is_selected = idx in selected_indices_list
            
            # Clases y Estilos dinámicos (Coinciden con el Clientside Callback)
            if is_selected:
                card_style = {
                    'transition': 'all 0.2s ease-in-out', 
                    'border': '2px solid #0d6efd', 
                    'backgroundColor': '#f0f8ff', 
                    'transform': 'scale(1.02)', 
                    'cursor': 'pointer'
                }
                card_class = "h-100 shadow"
            else:
                card_style = {
                    'transition': 'all 0.2s ease-in-out', 
                    'border': '1px solid rgba(0,0,0,0.125)', 
                    'backgroundColor': 'white', 
                    'transform': 'scale(1)', 
                    'cursor': 'pointer'
                }
                card_class = "h-100 shadow-sm hover-shadow"

            # 4. Construcción de la Tarjeta (Diseño Grid IDÉNTICO A GGA)
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        # Checkbox (Posición Absoluta)
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=[idx] if is_selected else [],
                                id={'type': 'enrichment-card-checkbox', 'index': idx}, # ID Específico de Enrichment
                                switch=True,
                                style={'transform': 'scale(1.3)'}
                            )
                        ], style={'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': '10'}),

                        html.Div([
                            # Header
                            html.Div([
                                html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                                dbc.Badge(badge_text, color=badge_color, style={'fontSize': '0.75rem'}),
                            ], className="d-flex align-items-center mb-2"),
                            
                            # Título truncado
                            html.H6(
                                item_name, 
                                className="fw-bold mb-2 text-truncate", 
                                title=item_name, 
                                style={'maxWidth': '90%'} 
                            ),
                            
                            html.Hr(className="my-2"),
                            
                            # Stats Line
                            html.Div([
                                html.Span(stats_text_left, className="fw-bold text-primary"),
                                html.Span(" | ", className="text-muted mx-1"),
                                html.Span(stats_text_right, className="text-muted text-truncate", style={'maxWidth': '120px', 'display': 'inline-block', 'verticalAlign': 'bottom'})
                            ], className="small mb-2"),
                            
                            # Comentario
                            html.P(
                                item_comment, 
                                className="text-muted small fst-italic mb-0 text-truncate",
                                title=item_comment
                            ) if item_comment else None,
                                   
                             # Footer
                            html.Div([
                                html.Small(f"Via: {item_origin}", className="text-muted", style={'fontSize': '0.65rem'})
                            ], className="mt-2 pt-1 border-top")

                        ], style={'paddingRight': '25px'}) 
                    ], className="p-3")
                ],
                id={'type': 'enrichment-card-wrapper', 'index': idx}, # ID para Clientside Callback
                className=card_class, 
                style=card_style)
            ], width=12, md=6, lg=4, xl=3, className="mb-3") # Grid Adaptativo igual a GGA

            cards.append(card)

        if not cards:
            return html.P("No compatible items found.", className="text-muted text-center py-4")
        
        return dbc.Row(cards, className="g-3")


    # 2. Callback de selección
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input({'type': 'enrichment-card-checkbox', 'index': ALL}, 'value'), 
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def update_enrichment_selection(list_of_checkbox_values, items):
        ctx = dash.callback_context
        if not ctx.triggered or not items:
            raise PreventUpdate
        
        selected_indices = {values[0] for values in list_of_checkbox_values if values}
        selected_indices_list = sorted(list(selected_indices))
        
        if not selected_indices_list:
            return selected_indices_list, html.Div(dbc.Alert("No items selected. Select items above to view the combined gene list.", color="info", className="mt-3"))

        combined_genes = set()
        for idx in selected_indices_list:
            if idx < len(items):
                item = items[idx]
                item_type = item.get('type', '')
                
                if item_type == 'solution':
                    combined_genes.update(item.get('data', {}).get('selected_genes', []))
                elif item_type == 'solution_set':
                    solutions = item.get('data', {}).get('solutions', [])
                    for sol in solutions:
                        combined_genes.update(sol.get('selected_genes', []))
                elif item_type in ['gene_set', 'combined_gene_group']:
                    combined_genes.update(item.get('data', {}).get('genes', []))
                elif item_type == 'individual_gene':
                    combined_genes.add(item.get('data', {}).get('gene', ''))

        gene_count = len(combined_genes)
        
        gene_string = ""
        if combined_genes:
            cleaned_genes = {g for g in combined_genes if g and isinstance(g, str)}
            if cleaned_genes:
                gene_string = " ".join(sorted(list(cleaned_genes)))
        
        summary_panel = dbc.Alert([
            html.H6("Combined Input IDs for Analysis (Input Set)", className="alert-heading"),
            html.P(f"Total Unique IDs (Probes/Genes): {gene_count}", className="mb-1"),
            html.P(f"Source Items: {len(selected_indices_list)}", className="mb-0"),
            
            html.Div([
                html.Details([
                    html.Summary("View Input ID List", 
                                 style={'cursor': 'pointer', 'color': 'inherit', 'fontWeight': 'bold'}),
                    html.P(', '.join(sorted(list(combined_genes))), className="mt-2 small")
                
                ], style={'flex': '1'}), 
                
                dcc.Clipboard(
                    content=gene_string,
                    id='dynamic-clipboard-btn',
                    style={
                        "display": "inline-block",
                        "color": "inherit", 
                        "fontSize": "1rem",
                        "marginLeft": "8px", 
                    },
                    title="Copy input ID list (space-separated)"
                )
            ], 
            style={'display': 'flex', 'alignItems': 'flex-start'}) if gene_count > 0 else None,
            
        ], color="primary", className="mt-3")
        
        return selected_indices_list, summary_panel
    
    
    # 2.5. Callback de limpiar selección
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input('clear-enrichment-selection-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_enrichment_selection(n_clicks):
        if n_clicks and n_clicks > 0:
            return [], html.Div(dbc.Alert("No items selected. Select items above to view the combined gene list.", color="info", className="mt-3"))
        raise PreventUpdate

    
    # 2.6. Visibilidad del botón Clear
    @app.callback(
        Output('clear-enrichment-btn-container', 'style'),
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_clear_selection_button(selected_indices):
        if selected_indices and len(selected_indices) > 0:
            return {'display': 'block'}
        return {'display': 'none'}


    # 3. Habilitar botones de análisis
    @app.callback(
        [Output('run-gprofiler-btn', 'disabled'),
         Output('run-reactome-btn', 'disabled')], 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices):
        is_disabled = not (selected_indices and len(selected_indices) > 0)
        return is_disabled, is_disabled
  
    
    # 4. Ejecutar g:Profiler
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         Output('gprofiler-spinner-output', 'children')], 
        Input('run-gprofiler-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('gprofiler-organism-dropdown', 'value'),
         State('gprofiler-sources-checklist', 'value'),
         State('gprofiler-target-namespace', 'value'),
         State('gprofiler-validation-switch', 'value')],
        prevent_initial_call=True
    )
    def run_gprofiler_analysis(n_clicks, selected_indices, items, organism, selected_sources, target_namespace, use_validation):
        if not n_clicks or not selected_indices:
            raise PreventUpdate
        
        combined_genes_dirty = set()
        for idx in selected_indices:
            if idx < len(items):
                item = items[idx]
                item_type = item.get('type', '')
                if item_type == 'solution': combined_genes_dirty.update(item.get('data', {}).get('selected_genes', []))
                elif item_type == 'solution_set':
                    for sol in item.get('data', {}).get('solutions', []): combined_genes_dirty.update(sol.get('selected_genes', []))
                elif item_type in ['gene_set', 'combined_gene_group']: combined_genes_dirty.update(item.get('data', {}).get('genes', []))
                elif item_type == 'individual_gene': combined_genes_dirty.add(item.get('data', {}).get('gene', ''))
        
        gene_list_raw_dirty = [g for g in combined_genes_dirty if g and isinstance(g, str)]
        gene_list_to_validate = [g for g in gene_list_raw_dirty if g] 
        gene_list_original_count = len(set(gene_list_to_validate))

        if not gene_list_to_validate:
            return {'results': [], 'gene_list_validated': [], 'gene_list_original_count': 0, 'organism': organism}, None

        clean_gene_list = []
        
        if use_validation:
            validation_response = GProfilerService.validate_genes(gene_list_to_validate, organism, target_namespace=target_namespace)
            clean_gene_list = validation_response.get('validated_genes', [])
        else:
            clean_gene_list = sorted(list(set(gene_list_to_validate)))
        
        if not clean_gene_list:
            return {'results': [], 'gene_list_validated': [], 'gene_list_original_count': gene_list_original_count, 'organism': organism}, None

        full_response = GProfilerService.get_enrichment(clean_gene_list, organism, selected_sources)

        if full_response is None:
            return {'results': None, 'gene_list_validated': clean_gene_list, 'gene_list_original_count': gene_list_original_count, 'organism': organism}, None 

        enrichment_data_list = full_response.get('result', [])
        metadata = full_response.get('meta', {})
        
        query_key = next(iter(metadata.get('genes_metadata', {}).get('query', {})), None)
        
        if not query_key:
             mapped_ensg_list = []
             ensg_to_input_map = {}
        else:
            query_metadata = metadata['genes_metadata']['query'][query_key]
            mapping_dict = query_metadata.get('mapping', {})
            mapped_ensg_list = query_metadata.get('ensgs', [])
            
            ensg_to_input_map = {}
            for input_id, ensg_list in mapping_dict.items():
                for ensg in ensg_list:
                    ensg_to_input_map[ensg] = input_id

        if not enrichment_data_list:
            return {'results': [], 'gene_list_validated': clean_gene_list, 'gene_list_original_count': gene_list_original_count, 'organism': organism}, None

        final_enrichment_data = []
        for term in enrichment_data_list:
            intersection_genes_input_ids = set()
            intersections_flags = term.get('intersections', [])
            
            if not mapped_ensg_list and not use_validation:
                pass 

            for i, flag in enumerate(intersections_flags):
                if i < len(mapped_ensg_list) and flag:
                    ensg_id = mapped_ensg_list[i]
                    input_id = ensg_to_input_map.get(ensg_id)
                    if input_id:
                        intersection_genes_input_ids.add(input_id)
            
            intersection_list = sorted(list(intersection_genes_input_ids))
            
            new_term_data = {
                'source': term.get('source', ''),
                'term_name': term.get('name', ''), 
                'description': term.get('description', ''),
                'p_value': term.get('p_value', 1.0),
                'term_size': term.get('term_size', 0),
                'intersection_size': len(intersection_list),
                'precision': term.get('precision', 0.0),
                'recall': term.get('recall', 0.0),
                'source_order_display': str(term.get('source_order', 'N/A')), 
                'intersection_genes': intersection_list
            }
            final_enrichment_data.append(new_term_data)

        return {
            'results': final_enrichment_data, 
            'gene_list_validated': clean_gene_list, 
            'gene_list_original_count': gene_list_original_count, 
            'organism': organism
        }, None


    # 4.5. Mostrar resultados g:Profiler
    @app.callback(
        [Output('gprofiler-results-content', 'children', allow_duplicate=True),
         Output('clear-gprofiler-results-btn', 'disabled', allow_duplicate=True),
         Output('gprofiler-manhattan-plot', 'figure', allow_duplicate=True)], 
        [Input('gprofiler-results-store', 'data'),
         Input('gprofiler-threshold-input', 'value')], 
        [State('main-tabs', 'active_tab'),
         State('enrichment-service-tabs', 'active_tab')], 
        prevent_initial_call=True
    )
    def display_gprofiler_results(stored_data, threshold_value, main_active_tab, service_active_tab):
        if main_active_tab != 'enrichment-tab':
            raise PreventUpdate
        
        organism_map = {'hsapiens': 'Homo sapiens', 'mmusculus': 'Mus musculus', 'rnorvegicus': 'Rattus norvegicus', 'drerio': 'Danio rerio', 'dmelanogaster': 'Drosophila melanogaster', 'celegans': 'Caenorhabditis elegans'}
        
        if not stored_data:
            return html.Div("Click 'Run g:Profiler Analysis' to display results.", className="text-muted text-center p-4"), True, go.Figure()

        if stored_data.get('results') is None:
             return dbc.Alert("Error connecting to g:Profiler API.", color="danger"), True, go.Figure()

        enrichment_data_list = stored_data.get('results', [])
        gene_list_validated = stored_data.get('gene_list_validated', [])
        gene_list_original_count = stored_data.get('gene_list_original_count', 0)
        
        organism_code = stored_data.get('organism', 'hsapiens')
        organism_selected_name = organism_map.get(organism_code, organism_code)
        genes_analyzed_count = len(gene_list_validated) 
        
        validated_gene_string = " ".join(sorted(gene_list_validated)) if gene_list_validated else ""

        df = pd.DataFrame(enrichment_data_list)
        try: val_threshold = float(threshold_value)
        except (TypeError, ValueError): val_threshold = 0.05
        if not (0 < val_threshold <= 1.0): val_threshold = 0.05
            
        if df.empty:
            filtered_df = pd.DataFrame()
            manhattan_fig = create_gprofiler_manhattan_plot(df, threshold_value) 
            display_df = pd.DataFrame()
            filter_message = "No results found."
        else:
            filtered_df = df[df['p_value'] < val_threshold].copy()
            filter_message = f"Filtered results (P-Value corrected < {val_threshold})"
            manhattan_fig = create_gprofiler_manhattan_plot(df.copy(), threshold_value)
            display_df = filtered_df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False]) if not filtered_df.empty else pd.DataFrame()
        
        if not display_df.empty:
             display_df = display_df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'source_order_display']].copy()
        
        input_message = f"**Input:** Total Probes/IDs: **{gene_list_original_count}** | Selected Organism: **{organism_selected_name}**"
        validation_message_md = f"**Validation:** Recognized Genes: **{genes_analyzed_count}**"
        
        validation_card = html.Div([
            html.Div([
                dcc.Markdown(validation_message_md, className="mb-0"),
                html.Details([
                    html.Summary(f"View {genes_analyzed_count} Validated Genes", 
                                 style={'cursor': 'pointer', 'fontWeight': 'bold', 'color': '#0d6efd', 'fontSize': '0.9rem', 'display': 'inline-block'}),
                    html.P(', '.join(sorted(gene_list_validated)), className="mt-2 small")
                ]) if genes_analyzed_count > 0 else None
            ], style={'flex': '1'}),
            
            dcc.Clipboard(
                content=validated_gene_string,
                id='gprofiler-clipboard-validated-genes',
                style={"display": "inline-block", "color": "#0d6efd", "fontSize": "1.1rem", "marginLeft": "10px"},
                title="Copy validated gene list"
            ) if genes_analyzed_count > 0 else None
        ], style={'display': 'flex', 'alignItems': 'flex-start', 'justifyContent': 'space-between'})
        
        if not display_df.empty:
            pathways_message = f"Displaying **{len(display_df)}** terms. {filter_message}"
        else:
             pathways_message = f"No significant pathways found after applying the filter ({val_threshold})."
        
        summary_content = [
            dcc.Markdown(pathways_message, className="mb-0"),
            dcc.Markdown(input_message, className="mb-0"),
            validation_card
        ]
        
        hidden_cols = ['source_order_display'] 
        column_map = {
            'p_value': {'name': 'P-Value', 'type': 'numeric', 'format': {'specifier': '.2e'}},
            'intersection_size': {'name': 'Genes\nMatched', 'type': 'numeric'},
            'term_size': {'name': 'Term\nSize', 'type': 'numeric'},
            'precision': {'name': 'Precision', 'type': 'numeric', 'format': {'specifier': '.3f'}},
            'recall': {'name': 'Recall', 'type': 'numeric', 'format': {'specifier': '.3f'}},
            'term_name': {'name': 'Term Name', 'type': 'text'},
            'description': {'name': 'Description', 'type': 'text'},
            'source': {'name': 'Source', 'type': 'text'},
            'source_order_display': {'name': 'Source\nOrder', 'type': 'text'},
        }
        display_columns = [{'name': column_map.get(col, {}).get('name', col.capitalize()), 'id': col, 'type': column_map.get(col, {}).get('type', 'text'), 'format': column_map.get(col, {}).get('format'), 'hideable': True} for col in display_df.columns]
        
        results_content = [
            html.H4("g:Profiler Enrichment Results", className="mb-3"),
            dbc.Card(dbc.CardBody(summary_content), className="mb-3", style={'whiteSpace': 'pre-line'}),
            dash_table.DataTable(
                id='enrichment-results-table-gprofiler', data=display_df.to_dict('records'), columns=display_columns,
                hidden_columns=hidden_cols, sort_action="native", filter_action="native", page_action="native", page_current=0, page_size=15,
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell_conditional=[
                    {'if': {'column_id': 'term_name'}, 'width': '15%', 'minWidth': '100px', 'textAlign': 'left'}, 
                    {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px', 'maxWidth': '350px', 'textAlign': 'left'},
                    {'if': {'column_id': 'p_value'}, 'width': '8%', 'minWidth': '70px', 'maxWidth': '80px', 'textAlign': 'center'},
                    {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                ],
                style_cell={'padding': '8px', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold', 'whiteSpace': 'normal', 'height': 'auto', 'padding': '10px 8px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                tooltip_duration=None,
            )
        ]
        
        if not display_df.empty:
            return html.Div(results_content), False, manhattan_fig
        else:
            alert_color = "info" if genes_analyzed_count > 0 else "warning"
            if genes_analyzed_count == 0 and gene_list_original_count > 0:
                 summary_content.append(dcc.Markdown("\n\n**Action Failed:** No input IDs were validated.", className="text-danger"))
            
            return html.Div(dbc.Alert(summary_content, color=alert_color, className="mt-3")), False, manhattan_fig

   # 4.6. Limpiar g:Profiler
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         Output('gprofiler-manhattan-plot', 'figure', allow_duplicate=True)], 
        Input('clear-gprofiler-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_gprofiler_results(n_clicks):
        if n_clicks and n_clicks > 0:
            empty_data = {
                'results': [], 
                'gene_list_validated': [], 
                'gene_list_original_count': 0,
                'organism': 'hsapiens'
            }
            return empty_data, go.Figure()
        raise PreventUpdate

    # 7. Limpiar Reactome
    @app.callback(
        Output('reactome-results-store', 'data', allow_duplicate=True),
        Input('clear-reactome-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_reactome_results(n_clicks):
        if n_clicks and n_clicks > 0:
            return {
                'results': [], 
                'gene_list_original': [], 
                'gene_list_validated': [], 
                'organism_selected': 'Homo sapiens'
            }
        raise PreventUpdate


  # --- CALLBACK UNIFICADO: REACTOME (RUN + CLEAR) ---
    @app.callback(
        [Output('reactome-results-store', 'data', allow_duplicate=True), 
         Output('reactome-spinner-output', 'children')],
        [Input('run-reactome-btn', 'n_clicks'),
         Input('clear-reactome-results-btn', 'n_clicks')],
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('reactome-organism-input', 'value'),
         State('reactome-options-checklist', 'value'),
         State('reactome-target-namespace', 'value'),
         State('reactome-validation-switch', 'value')],
        prevent_initial_call=True
    )
    def manage_reactome_analysis(run_clicks, clear_clicks, selected_indices, items, organism_name, selected_options, target_namespace, use_validation):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'clear-reactome-results-btn':
            return {
                'results': [], 
                'gene_list_original': [], 
                'gene_list_validated': [], 
                'organism_selected': 'Homo sapiens'
            }, None

        if trigger_id == 'run-reactome-btn':
            if not selected_indices:
                raise PreventUpdate
            
            options = selected_options or []
            projection = 'projection' in options
            include_disease = 'disease' in options
            interactors = 'interactors' in options
            
            combined = set()
            for idx in selected_indices:
                if idx < len(items):
                    item = items[idx]
                    itype = item.get('type')
                    if itype == 'solution': combined.update(item.get('data', {}).get('selected_genes', []))
                    elif itype == 'solution_set':
                        for s in item.get('data', {}).get('solutions', []): combined.update(s.get('selected_genes', []))
                    elif itype in ['gene_set', 'combined_gene_group']: combined.update(item.get('data', {}).get('genes', []))
                    elif itype == 'individual_gene': combined.add(item.get('data', {}).get('gene', ''))
            
            raw = [g for g in combined if g and isinstance(g, str)]
            
            clean = []
            if use_validation:
                val_res = GProfilerService.validate_genes(raw, 'hsapiens', target_namespace=target_namespace)
                clean = val_res.get('validated_genes', [])
            else:
                clean = sorted(list(set(raw)))
            
            store = {'results': [], 'token': 'ERROR', 'gene_list_validated': clean, 'gene_list_original': raw}
            
            if not clean: 
                return store, None
            
            try:
                res = ReactomeService.get_enrichment(
                    clean, 
                    organism_name=organism_name,
                    projection=projection,
                    interactors=interactors,
                    include_disease=include_disease
                )
            except Exception as e:
                 logger.error(f"CRITICAL CRASH in ReactomeService: {e}")
                 return store, None

            if res:
                res['gene_list_original'] = raw
                res['gene_list_validated'] = clean
                return res, None
            
            return store, None
        
        raise PreventUpdate

    # 5.5 Mostrar resultados Reactome
    @app.callback(
        [Output('reactome-results-content', 'children'),
        Output('clear-reactome-results-btn', 'disabled'),
        Output('reactome-diagram-output', 'children', allow_duplicate=True),
        Output('reactome-fireworks-output', 'children', allow_duplicate=True)], 
        Input('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def display_reactome_results(stored_data):
        placeholder_diagram = html.Div(dbc.Alert("Select a pathway from the table above to visualize gene overlap.", color="secondary"), className="p-3")
        placeholder_fireworks = html.Div(dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info"), className="p-3")
        
        if stored_data is None or not isinstance(stored_data, dict):
            raise PreventUpdate
        
        enrichment_data_list = stored_data.get('results', [])
        analysis_token = stored_data.get('token', 'N/A')
        organism_used_api = stored_data.get('organism_used_api', 'N/A')
        organism_selected = stored_data.get('organism_selected', 'N/A')
        
        gene_list_original = stored_data.get('gene_list_original', [])
        gene_list_validated = stored_data.get('gene_list_validated', [])
        
        genes_original_count = len(set(gene_list_original))
        genes_validated_count = len(set(gene_list_validated))
        
        validated_gene_string = " ".join(sorted(gene_list_validated)) if gene_list_validated else ""
        
        fireworks_content = placeholder_fireworks
        if analysis_token and analysis_token not in ['N/A', 'ERROR'] and organism_used_api and len(enrichment_data_list) > 0:
            organism_encoded = organism_used_api.replace(' ', '%20')
            fireworks_url = f"https://reactome.org/PathwayBrowser/?species={organism_encoded}#DTAB=AN&ANALYSIS={analysis_token}"
            
            fireworks_content = html.Iframe(
                src=fireworks_url, 
                style={"width": "100%", "height": "500px", "border": "none"}, 
                title=f"Reactome Fireworks for {organism_used_api}", 
                tabIndex="-1" 
            )
        
        input_message = f"**Input:** Total Probes/IDs: **{genes_original_count}** | Selected Organism: **{organism_selected}**"
        validation_message_md = f"**Validation:** Recognized Genes: **{genes_validated_count}**"
        
        validation_card = html.Div([
            html.Div([
                dcc.Markdown(validation_message_md, className="mb-0"),
                html.Details([
                    html.Summary(f"View {genes_validated_count} Validated Genes", 
                                 style={'cursor': 'pointer', 'fontWeight': 'bold', 'color': '#0d6efd', 'fontSize': '0.9rem', 'display': 'inline-block'}),
                    html.P(', '.join(sorted(gene_list_validated)), className="mt-2 small")
                ]) if genes_validated_count > 0 else None
            ], style={'flex': '1'}),
            
            dcc.Clipboard(
                content=validated_gene_string,
                id='reactome-clipboard-validated-genes',
                style={"display": "inline-block", "color": "#0d6efd", "fontSize": "1.1rem", "marginLeft": "10px"},
                title="Copy validated gene list"
            ) if genes_validated_count > 0 else None
        ], style={'display': 'flex', 'alignItems': 'flex-start', 'justifyContent': 'space-between'})
        
        output_message = f"**Analysis:** Validated Organism (API): **{organism_used_api}** | Analysis Token: **{analysis_token}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant Reactome pathways."
        
        summary_content = [
            dcc.Markdown(pathways_message, className="mb-0"),
            html.Hr(style={'margin': '0.5rem 0'}),
            dcc.Markdown(input_message, className="mb-0"),
            validation_card, 
            html.Hr(style={'margin': '0.5rem 0'}),
            dcc.Markdown(output_message, className="mb-0")
        ]

        if analysis_token == 'ERROR':
            summary_content = [
                dbc.Alert("An error occurred connecting to the Reactome service.", color="danger"),
                html.Hr(style={'margin': '0.5rem 0'}),
                dcc.Markdown(input_message, className="mb-0"),
                validation_card,
            ]
        
        if not enrichment_data_list:
            if analysis_token == 'N/A' and genes_original_count > 0:
                summary_content.insert(0, dcc.Markdown("No analysis run (0 validated genes).", className="text-warning"))
            elif analysis_token != 'ERROR' and analysis_token != 'N/A':
                 summary_content[0] = dcc.Markdown("No significant pathways found in Reactome.", className="text-info")

            results_content = html.Div(dbc.Card(dbc.CardBody(summary_content), className="mt-3", style={'whiteSpace': 'pre-line'}))
            return results_content, False, placeholder_diagram, fireworks_content

        df = pd.DataFrame(enrichment_data_list).sort_values(by=['fdr_value', 'entities_found'], ascending=[True, False])
        display_df = df[['term_name', 'description', 'fdr_value', 'p_value', 'entities_found', 'entities_total']].copy()
        
        hidden_cols = ['description']
        column_map = {
            'fdr_value': {'name': 'FDR\n(Corrected P-Value)', 'type': 'numeric', 'format': {'specifier': '.2e'}},
            'p_value': {'name': 'P-Value', 'type': 'numeric', 'format': {'specifier': '.2e'}},
            'entities_found': {'name': 'Genes\nMatched', 'type': 'numeric'},
            'entities_total': {'name': 'Pathway\nSize', 'type': 'numeric'},
            'term_name': {'name': 'Pathway Name', 'type': 'text'},
            'description': {'name': 'ST_ID', 'type': 'text'},
        }
        display_columns = [{'name': column_map.get(col, {}).get('name', col.capitalize()), 'id': col, 'type': column_map.get(col, {}).get('type', 'text'), 'format': column_map.get(col, {}).get('format'), 'hideable': True} for col in display_df.columns]

        results_content = [
            html.H4("Reactome Enrichment Results", className="mb-3"), 
            dbc.Card(dbc.CardBody(summary_content), className="mb-3", style={'whiteSpace': 'pre-line'}),
            dash_table.DataTable(
                id='enrichment-results-table-reactome', data=display_df.to_dict('records'), columns=display_columns,
                hidden_columns=hidden_cols, row_selectable='single', selected_rows=[],
                sort_action="native", filter_action="native", page_action="native", page_current=0, page_size=10,
                style_table={'overflowX': 'auto', 'minWidth': '100%'}, 
                style_cell_conditional=[
                    {'if': {'column_id': 'term_name'}, 'width': '50%', 'minWidth': '150px', 'textAlign': 'left'},
                    {'if': {'column_id': 'fdr_value'}, 'width': '15%', 'minWidth': '70px', 'maxWidth': '90px'},
                    {'if': {'column_id': 'p_value'}, 'width': '15%', 'minWidth': '70px', 'maxWidth': '90px'},
                    {'if': {'column_id': 'entities_found'}, 'width': '10%', 'minWidth': '50px', 'maxWidth': '70px'},
                ],
                style_cell={'textAlign': 'center', 'padding': '8px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold', 'whiteSpace': 'normal', 'height': 'auto', 'padding': '10px 8px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                tooltip_data=[{'description': {'value': row['description'], 'type': 'text'}} for row in display_df.to_dict('records')],
                tooltip_duration=None,
            )
        ]
        return html.Div(results_content), False, placeholder_diagram, fireworks_content

    # 6. Visualizar Diagrama Reactome
    @app.callback(
        [Output('reactome-diagram-output', 'children', allow_duplicate=True),
         Output('reactome-diagram-spinner-output', 'children')], 
        Input('enrichment-results-table-reactome', 'selected_rows'), 
        State('enrichment-results-table-reactome', 'data'),
        State('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def visualize_reactome_diagram(selected_rows, table_data, stored_results):
        if not selected_rows or not table_data:
            raise PreventUpdate
        
        placeholder_alert = html.Div(dbc.Alert("Select a pathway from the table to visualize gene overlap.", color="secondary"), className="p-3")

        if not stored_results or stored_results.get('token') in [None, 'N/A', 'ERROR'] or stored_results.get('token').startswith('REF_'):
            return placeholder_alert, None

        analysis_token = stored_results['token']
        selected_index = selected_rows[0]
        selected_pathway_data = table_data[selected_index]
        pathway_st_id = selected_pathway_data.get('description')
        pathway_name = selected_pathway_data.get('term_name')

        if not pathway_st_id:
            return html.Div(dbc.Alert("Error: Could not find Pathway Stable ID (ST_ID).", color="danger"), className="p-3"), None
        
        image_base64_string = ReactomeService.get_diagram_image_base64(
            pathway_st_id=pathway_st_id, 
            analysis_token=analysis_token
        )
        
        if image_base64_string is None:
            return html.Div(dbc.Alert("Error: Could not download the pathway diagram from Reactome.", color="danger"), className="p-3"), None

        diagram_content = html.Div([
            html.H5(f"Pathway Visualization: {pathway_name}", className="mt-3"),
            html.P(f"Stable ID: {pathway_st_id}", className="text-muted small"),
            html.A(
                html.Img(
                    src=image_base64_string, 
                    alt=f"Reactome Diagram for {pathway_name}", 
                    style={'maxWidth': '100%', 'height': 'auto', 'border': '1px solid #ddd', 'borderRadius': '5px'}
                ),
                href=f"https://reactome.org/content/detail/{pathway_st_id}?analysis={analysis_token}",
                target="_blank",
                className="d-block mt-3"
            ),
            html.P(html.Strong("Click the image to view the interactive diagram on Reactome.org"), className="text-center text-info small mt-2")
        ], className="mt-4 p-3 border rounded shadow-sm")
        
        return diagram_content, None

            
    # 7.5. Ajuste de tabla
    @app.callback(
        [Output('enrichment-results-table-gprofiler', 'style_header_conditional', allow_duplicate=True),
        Output('enrichment-results-table-gprofiler', 'style_data_conditional', allow_duplicate=True)],
        Input('enrichment-results-table-gprofiler', 'columns'),
        State('enrichment-results-table-gprofiler', 'style_data_conditional'),
        prevent_initial_call=True
    )
    def adjust_gprofiler_column_widths_dynamically(current_columns, base_style_data_conditional):
        if current_columns is None:
            raise PreventUpdate
        return [], base_style_data_conditional
            
            
    # 8. Callback para Heatmap
    @app.callback(
        Output('gprofiler-clustergram-output', 'children'),
        [Input('gprofiler-results-store', 'data'),      
        Input('gprofiler-threshold-input', 'value')], 
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def display_gprofiler_clustergram(stored_data, threshold_value, selected_indices, items):
        if not stored_data or isinstance(stored_data, list):
            return dbc.Alert(
                "Ejecute un análisis de g:Profiler para generar el clustergram.",
                color="info",
                className="mt-3"
            )

        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05 

        heatmap_matrix, debug_counters = process_data_for_gene_term_heatmap(stored_data, threshold=val_threshold, max_terms=50) 
        
        if heatmap_matrix.empty:
            if not stored_data or (stored_data.get('results') is None):
                 detail_message = "No analysis data found. Run g:Profiler analysis first."
            elif not stored_data.get('gene_list_validated'):
                 detail_message = "No validated genes were found after g:Convert sanitation."
            elif debug_counters['terms_after_pvalue_filter'] == 0:
                detail_message = f"No terms passed the P-value filter (< {val_threshold})."
            elif debug_counters['terms_removed_by_zerovariance'] > 0 or debug_counters['genes_removed_by_zerovariance'] > 0:
                 detail_message = "All terms/genes were removed during zero-variance cleaning."
            else:
                 detail_message = "No significant gene-term associations found to plot."
            
            return dbc.Alert([
                html.H6("Clustergram could not be generated.", className="alert-heading"),
                html.P(detail_message)
            ], color="info")

        heatmap_fig = create_gene_term_heatmap(heatmap_matrix)

        return dcc.Graph(figure=heatmap_fig, config={'displayModeBar': True})