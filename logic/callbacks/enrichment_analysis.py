# logic/callbacks/enrichment_analysis.py (CÓDIGO COMPLETO CON TODAS LAS CORRECCIONES)

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
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

# --- FUNCIÓN DE MANHATTAN PLOT (Sin Cambios) ---
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
    source_order = ['GO:BP', 'GO:MF', 'GO:CC', 'KEGG', 'REAC']
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
    
    # Cambio
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
    
    source_labels = df_plot.groupby('source', observed=True)['term_index'].agg(['min', 'max']).reset_index() 
    source_labels['center'] = (source_labels['min'] + source_labels['max']) / 2
    
    fig.update_layout(
        xaxis={'title': "Functional Enrichment Terms (Grouped by Source)", 'tickmode': 'array', 'tickvals': source_labels['center'], 'ticktext': source_labels['source'], 'showgrid': False, 'zeroline': False, 'tickangle': 0},
        yaxis={'title': '-log10(P-value)', 'automargin': True},
        showlegend=True,
        height=550,
        margin={'t': 30, 'b': 80, 'l': 50, 'r': 10}, 
        plot_bgcolor='white'
    )

    fig.add_hline(y=y_threshold, line_dash="dot", line_color="red", annotation_text=line_name, annotation_position="top right")

    fig.update_traces(
        marker=dict(opacity=0.6, line=dict(width=0.5, color='DarkSlateGrey')),
        hovertemplate="<b>Term:</b> %{customdata[0]}<br><b>Source:</b> %{customdata[3]}<br><b>-log10(P-value):</b> %{y:.2f}<br><b>P-value:</b> %{customdata[1]:.2e}<br><b>Genes Matched:</b> %{customdata[2]}<br><b>Gold Standard:</b> %{customdata[4]}<br><extra></extra>"
    )
    return fig

# --- FUNCIÓN DE PROCESAMIENTO DE HEATMAP (Sin Cambios) ---
def process_data_for_gene_term_heatmap(stored_data, threshold=0.05, max_terms=50):
    results = stored_data.get('results', [])
    gene_list_upper = stored_data.get('gene_list', []) 
    
    debug_counters = {
        'timestamp_start': datetime.now().strftime("%H:%M:%S.%f"), 'initial_terms': len(results), 'initial_genes': len(gene_list_upper), 'terms_after_pvalue_filter': 0,
        'terms_before_zerovariance_clean': 0, 'genes_before_zerovariance_clean': 0, 'terms_removed_by_zerovariance': 0, 'genes_removed_by_zerovariance': 0, 'timestamp_end': None
    }
    
    if not results or not gene_list_upper:
        return pd.DataFrame(), debug_counters

    df = pd.DataFrame(results)
    df['-log10(q-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    df_significant = df[df['p_value'] < threshold].sort_values(by='p_value', ascending=True).head(max_terms) 
    
    debug_counters['terms_after_pvalue_filter'] = len(df_significant)
    
    if df_significant.empty:
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    term_list = df_significant['term_name'].tolist()
    heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_upper)
    
    for _, row in df_significant.iterrows():
        term_name = row['term_name']
        log_q_value = row['-log10(q-value)'] 
        raw_intersecting_genes = row.get('intersection_genes', [])
        intersecting_genes_upper = [g.upper() for g in raw_intersecting_genes if g and isinstance(g, str)]
        
        for gene_upper in intersecting_genes_upper:
            if gene_upper in gene_list_upper:
                heatmap_matrix.loc[term_name, gene_upper] = log_q_value
                
    debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    return heatmap_matrix, debug_counters

# --- FUNCIÓN DE CREACIÓN DE HEATMAP (Sin Cambios) ---
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
    
    # 1. Callback de Actualización de IDs y Trigger (Sin Cambios)
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


    # 1.5. Callback de Renderizado Real (Sin Cambios)
    @app.callback(
        Output('enrichment-visual-selector', 'children'),
        Input('enrichment-render-trigger-store', 'data'),
        [State('interest-panel-store', 'data'),
         State('enrichment-selected-indices-store', 'data'),
         State('main-tabs', 'active_tab'),
         State('data-store', 'data')]
    )
    def render_visual_enrichment_selector(trigger_data, items, selected_indices_list, active_tab, data_store):
        if active_tab != 'enrichment-tab':
             raise PreventUpdate 

        if not items:
            return html.P("No items available. Add solutions, genes, or gene groups to your Interest Panel first.",
                         className="text-muted text-center py-4")

        all_solutions_dict = {}
        if data_store:
            for front in data_store.get("fronts", []):
                for sol in front["data"]:
                    all_solutions_dict[sol['solution_id']] = sol

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', '')
            item_comment = item.get('comment', '')

            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue
            
            if item_type == 'solution':
                badge_color, badge_text, icon = "primary", "Solution", "🔵"
                sol_data = item.get('data', {})
                sol_id = sol_data.get('id', 'Unknown')
                genes = sol_data.get('selected_genes', [])
                if not genes and sol_id in all_solutions_dict:
                    genes = all_solutions_dict[sol_id].get('selected_genes', [])
                gene_count = len(genes)
                front_name = sol_data.get('front_name', 'Unknown')
                description = f"{gene_count} genes | {front_name}"
            elif item_type == 'solution_set':
                badge_color, badge_text, icon = "info", "Solution Set", "📦"
                solutions = item.get('data', {}).get('solutions', [])
                unique_genes = set()
                for sol in solutions:
                    sol_id = sol.get('id', '')
                    genes = sol.get('selected_genes', [])
                    if not genes and sol_id in all_solutions_dict:
                        genes = all_solutions_dict[sol_id].get('selected_genes', [])
                    unique_genes.update(genes)
                gene_count = len(unique_genes)
                description = f"{len(solutions)} solutions | {gene_count} unique genes"
            elif item_type == 'gene_set':
                badge_color, badge_text, icon = "success", "Gene Group", "🧬"
                genes = item.get('data', {}).get('genes', [])
                frequency = item.get('data', {}).get('frequency', 'N/A')
                description = f"{len(genes)} genes | Freq: {frequency}%"
            elif item_type == 'individual_gene':
                badge_color, badge_text, icon = "warning", "Gene", "🔬"
                gene = item.get('data', {}).get('gene', 'Unknown')
                description = f"Gene: {gene}"
            elif item_type == 'combined_gene_group':
                badge_color, badge_text, icon = "success", "Combined Group", "🎯"
                gene_count = item.get('data', {}).get('gene_count', 0)
                source_count = len(item.get('data', {}).get('source_items', []))
                description = f"{gene_count} genes | {source_count} sources"
            else:
                continue

            is_selected = [idx] if idx in selected_indices_list else []
            
            card = dbc.Col(dbc.Card(dbc.CardBody([
                html.Div(dbc.Checklist(
                    options=[{"label": "", "value": idx}],
                    value=is_selected, 
                    id={'type': 'enrichment-card-checkbox', 'index': idx}, 
                    switch=True,
                    style={'transform': 'scale(1.3)'}
                ), style={'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': '10'}),
                html.Div([
                    html.Div([
                        html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                        dbc.Badge(badge_text, color=badge_color, className="ms-1", style={'fontSize': '0.7rem'})
                    ], className="d-flex align-items-center mb-1"),
                    html.Strong(item_name, className="d-block mb-1", style={'fontSize': '0.9rem'}),
                    html.P(description, className="text-muted small mb-1", style={'fontSize': '0.75rem'}),
                    html.P(item_comment, className="text-muted small fst-italic mb-0", style={'fontSize': '0.7rem'}) if item_comment else None
                ], style={'paddingRight': '40px'})
            ], className="p-2", style={'minHeight': '120px', 'position': 'relative'}), className="h-100 shadow-sm hover-shadow"), width=12, md=6, lg=3, className="mb-3")
            cards.append(card)

        if not cards:
            return html.P("No compatible items found.", className="text-muted text-center py-4")
        return dbc.Row(cards, className="g-3")


    # 2. Callback de selección (CORREGIDO con allow_duplicate)
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
        
        summary_panel = dbc.Alert([
            html.H6("Combined Genes for Enrichment (Input Set)", className="alert-heading"),
            html.P(f"Total Unique Genes: {gene_count}", className="mb-1"),
            html.P(f"Source Items: {len(selected_indices_list)}", className="mb-0"),
            html.Details([
                html.Summary("View Gene List", style={'cursor': 'pointer', 'color': 'inherit', 'fontWeight': 'bold'}),
                html.P(', '.join(sorted(list(combined_genes))), className="mt-2 small")
            ]) if gene_count > 0 else None,
        ], color="primary", className="mt-3")
        
        return selected_indices_list, summary_panel
    
    # 2.5. Callback de limpiar selección (CORREGIDO con allow_duplicate)
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

    # 2.6. Visibilidad del botón Clear (Sin Cambios)
    @app.callback(
        Output('clear-enrichment-btn-container', 'style'),
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_clear_selection_button(selected_indices):
        if selected_indices and len(selected_indices) > 0:
            return {'display': 'block', 'height': '100%'}
        return {'display': 'none', 'height': '100%'}


    # 3. Habilitar botones de análisis (Sin Cambios)
    @app.callback(
        [Output('run-gprofiler-btn', 'disabled'),
         Output('run-reactome-btn', 'disabled')], 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices):
        is_disabled = not (selected_indices and len(selected_indices) > 0)
        return is_disabled, is_disabled
  
    # 4. Ejecutar g:Profiler (CORREGIDO con Spinner y allow_duplicate)
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         Output('gprofiler-spinner-output', 'children')], 
        Input('run-gprofiler-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        State('gprofiler-organism-dropdown', 'value')],
        prevent_initial_call=True
    )
    def run_gprofiler_analysis(n_clicks, selected_indices, items, organism):
        if not n_clicks or not selected_indices:
            raise PreventUpdate
        
        combined_genes = set()
        for idx in selected_indices:
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
        
        gene_list_raw = [g for g in combined_genes if g and isinstance(g, str)]
        gene_list_upper = sorted([g.upper() for g in gene_list_raw])

        if not gene_list_upper:
            return {'results': [], 'gene_list': [], 'organism': organism}, None

        results = GProfilerService.get_enrichment(gene_list_upper, organism)

        if results is None:
            return None, None 
        
        if not results:
            return {'results': [], 'gene_list': gene_list_upper, 'organism': organism}, None

        enrichment_data_list = []
        for term in results:
            source_order_value = str(term.get('source_order', 'N/A'))
            intersections_flags = term.get('intersections', [])
            intersection_genes = []
            for i, flag in enumerate(intersections_flags):
                if i < len(gene_list_upper) and flag:
                    intersection_genes.append(gene_list_upper[i])
            
            enrichment_data_list.append({
                'source': term.get('source', ''),
                'term_name': term.get('name', ''), 
                'description': term.get('description', ''),
                'p_value': term.get('p_value', 1.0),
                'term_size': term.get('term_size', 0),
                'query_size': term.get('query_size', 0),
                'intersection_size': term.get('intersection_size', 0),
                'precision': term.get('precision', 0.0),
                'recall': term.get('recall', 0.0),
                'source_order_display': source_order_value, 
                'significant': term.get('significant', False),
                'intersection_genes': intersection_genes
            })

        return {
            'results': enrichment_data_list, 
            'gene_list': gene_list_upper, 
            'organism': organism
        }, None
    
    # 4.5. Mostrar resultados g:Profiler (Sin Cambios)
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
        
        if stored_data is None:
            return dbc.Alert("Error connecting to g:Profiler API.", color="danger"), True, go.Figure()

        enrichment_data_list = stored_data.get('results', [])
        gene_list = stored_data.get('gene_list', [])
        organism_code = stored_data.get('organism', 'hsapiens')
        organism_selected_name = organism_map.get(organism_code, organism_code)
        organism_validated_name = organism_map.get(organism_code, organism_code)
        genes_analyzed = len(gene_list)

        if not enrichment_data_list and not gene_list:
            return html.Div("Click 'Run g:Profiler Analysis' to display results.", className="text-muted text-center p-4"), True, go.Figure()
        
        df = pd.DataFrame(enrichment_data_list)
        
        try: val_threshold = float(threshold_value)
        except (TypeError, ValueError): val_threshold = 0.05
        if not (0 < val_threshold <= 1.0): val_threshold = 0.05
        
        filtered_df = df[df['p_value'] < val_threshold].copy()
        filter_message = f"Filtered results (P-Value corrected < {val_threshold})"
        # Cambio
        df_plot = df.copy()
        manhattan_fig = create_gprofiler_manhattan_plot(df_plot, threshold_value)
        
        display_df = filtered_df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False]) if not filtered_df.empty else pd.DataFrame()
        
        if not display_df.empty:
             display_df = display_df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'source_order_display']].copy()
        
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_validated_name}**"
        pathways_message = f"Displaying **{len(display_df)}** terms. {filter_message}" if not display_df.empty else f"No significant pathways found after applying the filter ({val_threshold})."
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
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
            html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="text-muted", style={'whiteSpace': 'pre-line'}),
            dash_table.DataTable(
                id='enrichment-results-table-gprofiler', data=display_df.to_dict('records'), columns=display_columns,
                hidden_columns=hidden_cols, sort_action="native", filter_action="native", page_action="native", page_current=0, page_size=15,
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell_conditional=[
                    {'if': {'column_id': 'term_name'}, 'width': '15%', 'minWidth': '100px', 'textAlign': 'left'}, 
                    {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px', 'maxWidth': '350px', 'textAlign': 'left'},
                    {'if': {'column_id': 'p_value'}, 'width': '8%', 'minWidth': '70px', 'maxWidth': '80px', 'textAlign': 'center'},
                    {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'term_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'precision'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'recall'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'source'}, 'width': '7%', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
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
            return html.Div(dbc.Alert(html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="mb-0"), color="info", className="mt-3")), False, manhattan_fig
        
    # 4.6. Limpiar g:Profiler (CORREGIDO con allow_duplicate)
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         Output('gprofiler-manhattan-plot', 'figure', allow_duplicate=True)], 
        Input('clear-gprofiler-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_gprofiler_results(n_clicks):
        if n_clicks and n_clicks > 0:
            return {'results': [], 'gene_list': [], 'organism': 'hsapiens'}, go.Figure()
        raise PreventUpdate

    # 5. Ejecutar Reactome (CORREGIDO con Spinner, allow_duplicate, check de seguridad y try...except)
    @app.callback(
        [Output('reactome-results-store', 'data', allow_duplicate=True), 
         Output('reactome-spinner-output', 'children')], 
        Input('run-reactome-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        State('reactome-organism-input', 'value')], 
        prevent_initial_call=True
    )
    def run_reactome_analysis(n_clicks, selected_indices, items, organism_name):
        if not n_clicks or not selected_indices:
            raise PreventUpdate

        combined_genes = set()
        for idx in selected_indices:
            if idx < len(items): # <-- Check de seguridad
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
        
        gene_list = [g for g in combined_genes if g and isinstance(g, str)]
        genes_analyzed_count = len(gene_list)

        error_data = {
            'results': [], 'token': 'ERROR', 'organism_used_api': 'N/A', 
            'organism_selected': organism_name, 'genes_analyzed': genes_analyzed_count, 'gene_list': []
        }

        if not gene_list:
            error_data['token'] = 'N/A'
            return error_data, None

        try:
            service_response = ReactomeService.get_enrichment(gene_list, organism_name)

        except Exception as e:
            logger.error(f"CRITICAL CRASH in ReactomeService: {e}")
            return error_data, None

        if service_response is None:
            logger.warning("ReactomeService returned None (handled error).")
            return error_data, None
        
        service_response['gene_list'] = gene_list
        
        return service_response, None

    # logic/callbacks/enrichment_analysis.py (Reemplazar el Callback 5.5)

    # 5.5 Mostrar resultados Reactome (MODIFICADO para el scroll)
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
        gene_list = stored_data.get('gene_list', [])
        genes_analyzed = len(gene_list)
        
        fireworks_content = placeholder_fireworks
        if analysis_token and analysis_token not in ['N/A', 'ERROR'] and organism_used_api and len(enrichment_data_list) > 0:
            organism_encoded = organism_used_api.replace(' ', '%20')
            fireworks_url = f"https://reactome.org/PathwayBrowser/?species={organism_encoded}#DTAB=AN&ANALYSIS={analysis_token}"
            
            # 🔑 CORRECCIÓN DE SCROLL: Añadir tabIndex="-1" previene que el Iframe
            # robe el foco del navegador y cause un scroll automático.
            fireworks_content = html.Iframe(
                src=fireworks_url, 
                style={"width": "100%", "height": "500px", "border": "none"}, 
                title=f"Reactome Fireworks for {organism_used_api}", 
                tabIndex="-1" 
            )

        # ... (El resto de la función para generar la tabla es idéntica) ...
        
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_used_api}** | Analysis Token: **{analysis_token}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant Reactome pathways."
        
        if analysis_token == 'ERROR':
            summary_message_md = f"An error occurred connecting to the Reactome service.\n\n{input_message}"
        else:
            summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        if not enrichment_data_list:
            simplified_no_results_message = f"No significant pathways found in Reactome.\n\n{input_message}"
            if analysis_token == 'ERROR':
                 simplified_no_results_message = f"Error connecting to Reactome API.\n\n{input_message}"
            
            results_content = html.Div(dbc.Alert(html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0"), color="info", className="mt-3"))
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
            html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="text-muted", style={'whiteSpace': 'pre-line'}),
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
                    {'if': {'column_id': 'entities_total'}, 'width': '10%', 'minWidth': '50px', 'maxWidth': '70px'},
                ],
                style_cell={'textAlign': 'center', 'padding': '8px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold', 'whiteSpace': 'normal', 'height': 'auto', 'padding': '10px 8px'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                tooltip_data=[{'description': {'value': row['description'], 'type': 'text'}} for row in display_df.to_dict('records')],
                tooltip_duration=None,
            )
        ]
        return html.Div(results_content), False, placeholder_diagram, fireworks_content

   # logic/callbacks/enrichment_analysis.py (Reemplazar el Callback 6)

    # logic/callbacks/enrichment_analysis.py (Reemplazar el Callback 6)

    # 6. Visualizar Diagrama Reactome (MODIFICADO para carga de imagen en servidor)
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
        
        # Placeholder por si el usuario des-selecciona
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

        # 🔑 CAMBIO CLAVE:
        # Ya no generamos una URL. Ahora llamamos a la función LENTA que
        # descarga la imagen y la devuelve como texto base64.
        # El spinner del header permanecerá activo mientras esta función se ejecuta.
        
        image_base64_string = ReactomeService.get_diagram_image_base64(
            pathway_st_id=pathway_st_id, 
            analysis_token=analysis_token
        )
        
        # Si la descarga falla, mostramos un error y apagamos el spinner.
        if image_base64_string is None:
            return html.Div(dbc.Alert("Error: Could not download the pathway diagram from Reactome.", color="danger"), className="p-3"), None

        # 🔑 CAMBIO CLAVE:
        # El 'src' del html.Img ahora es la cadena de datos base64.
        # El navegador no necesita hacer una nueva descarga; la imagen se carga al instante.
        diagram_content = html.Div([
            html.H5(f"Pathway Visualization: {pathway_name}", className="mt-3"),
            html.P(f"Stable ID: {pathway_st_id}", className="text-muted small"),
            html.A(
                html.Img(
                    src=image_base64_string,  # <--- Usamos la cadena base64
                    alt=f"Reactome Diagram for {pathway_name}", 
                    style={'maxWidth': '100%', 'height': 'auto', 'border': '1px solid #ddd', 'borderRadius': '5px'}
                ),
                href=f"https://reactome.org/content/detail/{pathway_st_id}?analysis={analysis_token}",
                target="_blank",
                className="d-block mt-3"
            ),
            html.P(html.Strong("Click the image to view the interactive diagram on Reactome.org"), className="text-center text-info small mt-2")
        ], className="mt-4 p-3 border rounded shadow-sm")
        
        # Retornamos el contenido y 'None' para apagar el spinner.
        return diagram_content, None

    # 7. Limpiar Reactome (CORREGIDO)
    @app.callback(
        Output('reactome-results-store', 'data', allow_duplicate=True),
        Input('clear-reactome-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_reactome_results(n_clicks):
        if n_clicks and n_clicks > 0:
            
            # 🔑 CORRECCIÓN: Este callback solo tiene UN Output ('reactome-results-store'),
            # por lo tanto, debe retornar UN solo valor (el diccionario).
            # Se eliminó el ", None" que estaba causando el error.
            
            return {'results': [], 'gene_list': [], 'organism': 'Homo sapiens'}
        
        raise PreventUpdate
            
    # 7.5. Ajuste de tabla (Sin Cambios)
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
            
            
    # 8. Callback para Heatmap (Sin Cambios)
    @app.callback(
        Output('gprofiler-clustergram-output', 'children'),
        [Input('gprofiler-results-store', 'data'),
        Input('gprofiler-threshold-input', 'value')],
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def display_gprofiler_clustergram(stored_data, threshold_value, selected_indices, items):
        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05 

        heatmap_matrix, debug_counters = process_data_for_gene_term_heatmap(stored_data, threshold=val_threshold, max_terms=50) 
        
        if heatmap_matrix.empty:
            if not stored_data or not stored_data.get('results'):
                 detail_message = "No analysis data found. Run g:Profiler analysis first."
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
 
