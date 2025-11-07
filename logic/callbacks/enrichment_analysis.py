# logic/callbacks/enrichment_analysis.py (CÓDIGO COMPLETO FINAL PARA ETAPA 2 CORREGIDA)

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

# Importamos AMBOS servicios
from services.gprofiler_service import GProfilerService 
from services.reactome_service import ReactomeService 

import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist, squareform

logger = logging.getLogger(__name__)

# --- FUNCIÓN DE MANHATTAN PLOT (SE MANTIENE IGUAL) ---
def create_gprofiler_manhattan_plot(df, threshold_value):
    """
    Crea un Manhattan Plot para los resultados de g:Profiler.
    El 'Gold Standard' es la línea de umbral.
    """
    
    line_threshold_value = 0.05 
    
    try:
        float_threshold = float(threshold_value)
        if 0 < float_threshold <= 1.0:
            line_threshold_value = float_threshold
    except (TypeError, ValueError):
        pass
    
    
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No significant terms to display in the Manhattan Plot.",
            xaxis={'visible': False},
            yaxis={'visible': False},
            height=400
        )
        return fig
        
    df['-log10(P-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    
    source_order = ['GO:BP', 'GO:MF', 'GO:CC', 'KEGG', 'REAC']
    df['source'] = pd.Categorical(df['source'], categories=source_order, ordered=True)
    df = df.sort_values(['source', 'p_value'], ascending=True)
    
    df['term_index'] = df.groupby('source', observed=True).cumcount() + 1
    
    y_threshold = -np.log10(line_threshold_value)
    line_name = f"Gold Standard Threshold (P < {line_threshold_value:.4f})" 
    
    df['is_gold_standard'] = df['-log10(P-value)'] >= y_threshold
    df['plot_color_group'] = df.apply(
        lambda row: 'Gold' if row['is_gold_standard'] else row['source'], axis=1
    )
    
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
        df['marker_size'] = (
            df['intersection_size'].clip(lower=0) * (max_size - min_size) / max_val
        ) + min_size
        
    df['marker_size'] = df['marker_size'].clip(upper=max_size)
    
    df_plot = df[df['significant'] == True].copy() 
    df_plot = df_plot.reset_index(drop=True) 

    
    if df_plot.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No significant terms found to plot.",
            xaxis={'visible': False},
            yaxis={'visible': False},
            height=400
        )
        return fig
        
    
    fig = px.scatter(
        df_plot, 
        x='term_index',
        y='-log10(P-value)',
        color='plot_color_group',
        color_discrete_map=color_map,
        size='marker_size', 
        custom_data=['term_name', 'p_value', 'intersection_size', 'source', 'is_gold_standard'],
        hover_data={
            'term_index': False, 
            '-log10(P-value)': ':.2f',
            'term_name': True,
            'p_value': ':.2e',
            'intersection_size': True,
            'source': True,
            'is_gold_standard': True
        }
    )
    
    source_labels = df_plot.groupby('source', observed=True)['term_index'].agg(['min', 'max']).reset_index() 
    source_labels['center'] = (source_labels['min'] + source_labels['max']) / 2
    
    fig.update_layout(
        xaxis={
            'title': "Functional Enrichment Terms (Grouped by Source)",
            'tickmode': 'array',
            'tickvals': source_labels['center'], 
            'ticktext': source_labels['source'], 
            'showgrid': False,
            'zeroline': False,
            'tickangle': 0 
        },
        yaxis={
            'title': '-log10(P-value)',
            'automargin': True
        },
        showlegend=True,
        height=550,
        margin={'t': 30, 'b': 80, 'l': 50, 'r': 10}, 
        plot_bgcolor='white'
    )

    fig.add_hline(
        y=y_threshold, 
        line_dash="dot", 
        line_color="red", 
        annotation_text=line_name, 
        annotation_position="top right"
    )

    fig.update_traces(
        marker=dict(
            opacity=0.6, 
            line=dict(width=0.5, color='DarkSlateGrey')
        ),
        hovertemplate=(
            "<b>Term:</b> %{customdata[0]}<br>"
            "<b>Source:</b> %{customdata[3]}<br>"
            "<b>-log10(P-value):</b> %{y:.2f}<br>"
            "<b>P-value:</b> %{customdata[1]:.2e}<br>"
            "<b>Genes Matched:</b> %{customdata[2]}<br>"
            "<b>Gold Standard:</b> %{customdata[4]}<br>"
            "<extra></extra>"
        )
    )

    return fig

# logic/callbacks/enrichment_analysis.py (Reemplazar la función process_data_for_gene_term_heatmap)

def process_data_for_gene_term_heatmap(stored_data, threshold=0.05, max_terms=50):
    """
    Procesa los resultados de g:Profiler para crear la matriz Term vs. Gen para el Heatmap.
    
    Args:
        stored_data (dict): Resultados de g:Profiler del store.
        threshold (float): P-Value (corregido) umbral para el filtrado inicial.
        max_terms (int): Número máximo de términos más significativos a incluir.
        
    Returns:
        pd.DataFrame: Matriz (Índice=Término, Columnas=Gen) con -log10(q-value) o 0.0.
        dict: Contadores de debug.
    """
    results = stored_data.get('results', [])
    gene_list_upper = stored_data.get('gene_list', []) 
    
    # 🔑 CORRECCIÓN CLAVE: Inicializar debug_counters aquí, antes de cualquier retorno.
    debug_counters = {
        'timestamp_start': datetime.now().strftime("%H:%M:%S.%f"), 
        'initial_terms': len(results),
        'initial_genes': len(gene_list_upper),
        'terms_after_pvalue_filter': 0,
        'terms_before_zerovariance_clean': 0, 
        'genes_before_zerovariance_clean': 0, 
        'terms_removed_by_zerovariance': 0,
        'genes_removed_by_zerovariance': 0,
        'timestamp_end': None
    }
    
    if not results or not gene_list_upper:
        # Si no hay datos iniciales, retorna el diccionario de debug inicializado
        return pd.DataFrame(), debug_counters

    df = pd.DataFrame(results)
    
    # 1. Calcular -log10(q-value) y Filtrar
    df['-log10(q-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    
    # VINCULACIÓN CRÍTICA: Usamos el umbral del Manhattan para el filtrado inicial
    df_significant = df[df['p_value'] < threshold].sort_values(
        by='p_value', 
        ascending=True
    ).head(max_terms) 

    
    debug_counters['terms_after_pvalue_filter'] = len(df_significant)
    
    if df_significant.empty:
        # Si el filtrado deja la tabla vacía, actualiza y retorna el debug_counters.
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    term_list = df_significant['term_name'].tolist()
    
    # 2. Inicializar la Matriz Term x Gen con 0.0
    heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_upper)
    
    # 3. Llenar la Matriz con -log10(q-value)
    for _, row in df_significant.iterrows():
        term_name = row['term_name']
        log_q_value = row['-log10(q-value)'] 
        
        raw_intersecting_genes = row.get('intersection_genes', [])
        
        # CRÍTICO: Convertimos la lista de intersección DE g:PROFILER a MAYÚSCULAS para cruzar.
        intersecting_genes_upper = [g.upper() for g in raw_intersecting_genes if g and isinstance(g, str)]
        
        for gene_upper in intersecting_genes_upper:
            if gene_upper in gene_list_upper:
                # El cruce ahora es robusto
                heatmap_matrix.loc[term_name, gene_upper] = log_q_value
                
    
    # --- 4. ELIMINAR FILAS Y COLUMNAS CON VARIANZA CERO ---
    
    debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    # Eliminación por cero-varianza
    heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    # 5. Actualizar Contadores de Debug
    debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    
    debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    return heatmap_matrix, debug_counters

    # term_list = df_significant['term_name'].tolist()
    
    # # 2. Inicializar la Matriz Term x Gen con 0.0
    # # Usamos los genes en mayúsculas como columnas (ya están en gene_list_upper)
    # heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_upper)
    
    # # 3. Llenar la Matriz con -log10(q_value)
    # for _, row in df_significant.iterrows():
    #     term_name = row['term_name']
    #     log_q_value = row['-log10(q_value)']
        
    #     raw_intersecting_genes = row.get('intersection_genes', [])
        
    #     # 🔑 CRUCE SIMPLIFICADO: Convertimos SOLO los genes de intersección a MAYÚSCULAS
    #     # para cruzar con la lista de columnas (gene_list_upper)
    #     intersecting_genes_upper = [g.upper() for g in raw_intersecting_genes if g and isinstance(g, str)]
        
    #     for gene_upper in intersecting_genes_upper:
    #         if gene_upper in gene_list_upper:
    #             # El cruce ahora es robusto: Mayúsculas vs. Mayúsculas
    #             heatmap_matrix.loc[term_name, gene_upper] = log_q_value
                
    
    # # --- 4. SOLUCIÓN AL ERROR: ELIMINAR FILAS Y COLUMNAS CON VARIANZA CERO ---
    
    # debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    # debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    # # Eliminación por cero-varianza
    # heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    # heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    # # 5. Actualizar Contadores de Debug
    # debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    # debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    
    # debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    # return heatmap_matrix, debug_counters

# logic/callbacks/enrichment_analysis.py (Reemplazar la función create_gene_term_heatmap)

def create_gene_term_heatmap(heatmap_matrix):
    """
    Genera el Heatmap (Clustergram) con clustering jerárquico.
    """
    if heatmap_matrix.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant gene-term associations remain after filtering.", height=400)
        return fig
    
    # --- 1. VALIDACIÓN DE TAMAÑO PARA CLUSTERING ---
    perform_row_clustering = heatmap_matrix.shape[0] >= 2
    perform_col_clustering = heatmap_matrix.shape[1] >= 2
    
    clustered_matrix = heatmap_matrix.copy()
    clustering_successful = True
    
    # --- 2. CLUSTERING JERÁRQUICO (CONDICIONAL) ---
    
    try:
        # Intento de clustering de filas (Términos)
        if perform_row_clustering:
            row_linkage = sch.linkage(pdist(clustered_matrix, metric='correlation'), method='average')
            row_order_indices = sch.dendrogram(row_linkage, orientation='right', no_plot=True)['leaves']
            clustered_matrix = clustered_matrix.iloc[row_order_indices, :]
        
        # Intento de clustering de columnas (Genes)
        if perform_col_clustering:
            col_linkage = sch.linkage(pdist(clustered_matrix.T, metric='correlation'), method='average')
            col_order_indices = sch.dendrogram(col_linkage, orientation='top', no_plot=True)['leaves']
            clustered_matrix = clustered_matrix.iloc[:, col_order_indices]
            
    except ValueError as e:
        logger.error(f"Clustering failed due to singular matrix (non-finite values in distance matrix): {e}. Plotting without clustering.")
        clustered_matrix = heatmap_matrix.copy()
        clustering_successful = False


    # --- 3. MAPA DE COLOR Y VALORES ---
    
    z_max = clustered_matrix.values.max()
    z_min = 0.0 
    
    colormap = px.colors.sequential.Plasma
    
    # --- 4. CREACIÓN DE LA FIGURA ---
    fig = go.Figure(data=go.Heatmap(
        z=clustered_matrix.values,
        x=clustered_matrix.columns,
        y=clustered_matrix.index,
        colorscale=colormap,
        zmin=z_min,
        zmax=z_max,
        showscale=True,
        colorbar=dict(
            title=dict(
                text='-log10(p-value)',
                side='right'
            ),
            thickness=15,
            len=0.7
        ),
        hovertemplate=(
            "<b>Term:</b> %{y}<br>"
            "<b>Gene:</b> %{x}<br>"
            "<b>-log10(p-value):</b> %{z:.2f}<br>"
            "<b>Membresía:</b> %{z} > 0 (Sí)<br>"
            "<extra></extra>"
        )
    ))

    # --- 5. LAYOUT FINAL ---
    
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
        height=min(max(50 * clustered_matrix.shape[0], 500), 1000), # Altura dinámica
        margin=dict(l=250, r=20, t=50, b=100)
    )

    return fig

    # term_list = df_significant['term_name'].tolist()
    
    # # 2. Inicializar la Matriz Term x Gen con 0.0
    # # Usamos los genes en mayúsculas como columnas (ya están en gene_list_upper)
    # heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_upper)
    
    # # 3. Llenar la Matriz con -log10(q_value)
    # for _, row in df_significant.iterrows():
    #     term_name = row['term_name']
    #     log_q_value = row['-log10(q_value)']
        
    #     raw_intersecting_genes = row.get('intersection_genes', [])
        
    #     # 🔑 CRUCE SIMPLIFICADO: Convertimos SOLO los genes de intersección a MAYÚSCULAS
    #     # para cruzar con la lista de columnas (gene_list_upper)
    #     intersecting_genes_upper = [g.upper() for g in raw_intersecting_genes if g and isinstance(g, str)]
        
    #     for gene_upper in intersecting_genes_upper:
    #         if gene_upper in gene_list_upper:
    #             # El cruce ahora es robusto: Mayúsculas vs. Mayúsculas
    #             heatmap_matrix.loc[term_name, gene_upper] = log_q_value
                
    
    # # --- 4. SOLUCIÓN AL ERROR: ELIMINAR FILAS Y COLUMNAS CON VARIANZA CERO ---
    
    # debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    # debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    # # Eliminación por cero-varianza
    # heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    # heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    # # 5. Actualizar Contadores de Debug
    # debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    # debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    
    # debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    # return heatmap_matrix, debug_counters

# --- INICIO DE REGISTERCALLBACKS ---
def register_enrichment_callbacks(app): 

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
        """
        Actualiza el Store de IDs seleccionadas y dispara el renderizado si la pestaña es activa.
        """
        ctx = dash.callback_context
        
        if not ctx.triggered:
            raise PreventUpdate
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'interest-panel-store':
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        if trigger_id == 'main-tabs' and active_tab == 'enrichment-tab':
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        if trigger_id == 'enrichment-selected-indices-store' and active_tab == 'enrichment-tab':
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        raise PreventUpdate


    # 1.5. Callback de Renderizado Real (Activado por el Trigger Store)
    @app.callback(
        Output('enrichment-visual-selector', 'children'),
        Input('enrichment-render-trigger-store', 'data'),
        [State('interest-panel-store', 'data'),
         State('enrichment-selected-indices-store', 'data'),
         State('main-tabs', 'active_tab'),
         State('data-store', 'data')]
    )
    def render_visual_enrichment_selector(trigger_data, items, selected_indices_list, active_tab, data_store):
        """Render visual card-based selector for enrichment analysis, ensuring late execution."""
        
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

            # Lógica de creación de tarjeta (se mantiene igual)
            
            if item_type == 'solution':
                badge_color = "primary"
                badge_text = "Solution"
                icon = "🔵"
                sol_data = item.get('data', {})
                sol_id = sol_data.get('id', 'Unknown')
                genes = sol_data.get('selected_genes', [])
                if not genes and sol_id in all_solutions_dict:
                    genes = all_solutions_dict[sol_id].get('selected_genes', [])
                gene_count = len(genes)
                front_name = sol_data.get('front_name', 'Unknown')
                description = f"{gene_count} genes | {front_name}"

            elif item_type == 'solution_set':
                badge_color = "info"
                badge_text = "Solution Set"
                icon = "📦"
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
                badge_color = "success"
                badge_text = "Gene Group"
                icon = "🧬"
                genes = item.get('data', {}).get('genes', [])
                frequency = item.get('data', {}).get('frequency', 'N/A')
                description = f"{len(genes)} genes | Freq: {frequency}%"

            elif item_type == 'individual_gene':
                badge_color = "warning"
                badge_text = "Gene"
                icon = "🔬"
                gene = item.get('data', {}).get('gene', 'Unknown')
                description = f"Gene: {gene}"

            elif item_type == 'combined_gene_group':
                badge_color = "success"
                badge_text = "Combined Group"
                icon = "🎯"
                gene_count = item.get('data', {}).get('gene_count', 0)
                source_count = len(item.get('data', {}).get('source_items', []))
                description = f"{gene_count} genes | {source_count} sources"
            else:
                continue

            is_selected = [idx] if idx in selected_indices_list else []
            
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=is_selected, 
                                id={'type': 'enrichment-card-checkbox', 'index': idx}, 
                                switch=True,
                                style={'transform': 'scale(1.3)'}
                            )
                        ], style={
                            'position': 'absolute',
                            'top': '10px',
                            'right': '10px',
                            'zIndex': '10'
                        }),
                        html.Div([
                            html.Div([
                                html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                                dbc.Badge(badge_text, color=badge_color, className="ms-1", style={'fontSize': '0.7rem'})
                            ], className="d-flex align-items-center mb-1"),
                            html.Strong(item_name, className="d-block mb-1", style={'fontSize': '0.9rem'}),
                            html.P(description, className="text-muted small mb-1", style={'fontSize': '0.75rem'}),
                            html.P(item_comment, className="text-muted small fst-italic mb-0", style={'fontSize': '0.7rem'}) if item_comment else None
                        ], style={'paddingRight': '40px'})
                    ], className="p-2", style={'minHeight': '120px', 'position': 'relative'})
                ], className="h-100 shadow-sm hover-shadow", style={'transition': 'all 0.2s'})
            ], width=12, md=6, lg=3, className="mb-3")

            cards.append(card)


        if not cards:
            return html.P("No compatible items found. Add solutions, genes, or gene groups to your Interest Panel first.", className="text-muted text-center py-4")

        return dbc.Row(cards, className="g-3")


    # 2. Callback para manejar la selección de los checkboxes, actualizar el Store y el panel de resumen
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data'),
         Output('enrichment-selection-panel', 'children')],
        Input({'type': 'enrichment-card-checkbox', 'index': ALL}, 'value'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def update_enrichment_selection(list_of_checkbox_values, items):
        """
        Escucha los checkboxes de las tarjetas, actualiza el Store de índices seleccionados 
        y renderiza el panel de resumen de genes combinados.
        """
        ctx = dash.callback_context
        
        if not ctx.triggered or not items:
            raise PreventUpdate
        
        selected_indices = set()
        for values in list_of_checkbox_values:
            if values:
                selected_indices.add(values[0])
        
        selected_indices_list = sorted(list(selected_indices))
        
        if not selected_indices_list:
            return selected_indices_list, html.Div("No items selected. Select items above to view the combined gene list.", className="text-muted p-3")

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
        
        summary_panel = dbc.Alert(
            [
                html.H6("Combined Genes for Enrichment (Input Set)", className="alert-heading"),
                html.P(f"Total Unique Genes: {gene_count}", className="mb-1"),
                html.P(f"Source Items: {len(selected_indices_list)}", className="mb-0"),
                html.Details([
                    html.Summary("View Gene List", style={'cursor': 'pointer', 'color': 'inherit', 'fontWeight': 'bold'}),
                    html.P(', '.join(sorted(list(combined_genes))), className="mt-2 small")
                ]) if gene_count > 0 else None,
            ],
            color="primary",
            className="mt-3"
        )
        
        return selected_indices_list, summary_panel
    
    # 2.5. Callback de limpiar la selección de tarjetas (NUEVO)
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input('clear-enrichment-selection-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_enrichment_selection(n_clicks):
        if n_clicks and n_clicks > 0:
            return [], html.Div("No items selected. Select items above to view the combined gene list.", className="text-muted p-3")
        raise PreventUpdate

    # 3. Callback para habilitar el botón de enriquecimiento (MODIFICADO para ambos botones)
    @app.callback(
        [Output('run-gprofiler-btn', 'disabled'),
         Output('run-reactome-btn', 'disabled')], 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices):
        """Habilitar/deshabilitar ambos botones de enriquecimiento si hay genes seleccionados."""
        is_disabled = not (selected_indices and len(selected_indices) > 0)
        return is_disabled, is_disabled
  

    # logic/callbacks/enrichment_analysis.py (Reemplazar la función run_gprofiler_analysis)

    # 4. Callback para ejecutar el análisis de g:Profiler (MODIFICADO CRÍTICAMENTE)
    @app.callback(
        Output('gprofiler-results-store', 'data'), 
        Input('run-gprofiler-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        State('gprofiler-organism-dropdown', 'value')],
        prevent_initial_call=True
    )
    def run_gprofiler_analysis(n_clicks, selected_indices, items, organism):
        """Executes g:Profiler enrichment analysis and stores results, including intersection genes."""
        if not n_clicks or not selected_indices:
            raise PreventUpdate
        
        # 1. Recolectar lista final de genes
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
        
        # 🔑 CRÍTICO: UNIFICAR EL CASO DE LOS GENES DE ENTRADA A MAYÚSCULAS 🔑
        gene_list_raw = [g for g in combined_genes if g and isinstance(g, str)]
        gene_list_upper = sorted([g.upper() for g in gene_list_raw])

        if not gene_list_upper:
            return {'results': [], 'gene_list': [], 'organism': organism}

        # 2. Ejecutar servicio de g:Profiler con la lista en mayúsculas
        results = GProfilerService.get_enrichment(gene_list_upper, organism)

        if results is None:
            return None 
        
        if not results:
            return {'results': [], 'gene_list': gene_list_upper, 'organism': organism}


        # 3. Procesar resultados de g:Profiler
        enrichment_data_list = []
        for term in results:
            
            source_order_value = str(term.get('source_order', 'N/A'))
            
            intersections_flags = term.get('intersections', [])
            
            # Extraer los genes que están en el pathway (donde intersections[i] no está vacío)
            intersection_genes = []
            for i, flag in enumerate(intersections_flags):
                if i < len(gene_list_upper) and flag:  # Si flag no está vacío, el gen está en el pathway
                    intersection_genes.append(gene_list_upper[i])
            
            print(f"[DEBUG MAPEO] Term: {term.get('name', 'Unknown')[:50]}")
            print(f"[DEBUG MAPEO] Intersections flags length: {len(intersections_flags)}")
            print(f"[DEBUG MAPEO] Gene list length: {len(gene_list_upper)}")
            print(f"[DEBUG MAPEO] Extracted genes: {len(intersection_genes)} - First 5: {intersection_genes[:5]}")
            
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
                'intersection_genes': intersection_genes  # Ahora contiene los genes reales
            })

        # Retorna la lista de genes de entrada en MAYÚSCULAS
        return {
            'results': enrichment_data_list, 
            'gene_list': gene_list_upper, 
            'organism': organism
        }
    # 4.5. Callback para mostrar los resultados de g:Profiler (MANTENIDO)
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
        
        organism_map = {
            'hsapiens': 'Homo sapiens', 'mmusculus': 'Mus musculus', 'rnorvegicus': 'Rattus norvegicus',
            'drerio': 'Danio rerio', 'dmelanogaster': 'Drosophila melanogaster', 'celegans': 'Caenorhabditis elegans',
        }

        enrichment_data_list = []
        gene_list = []
        organism_code = 'N/A'
        organism_selected_name = 'N/A'
        organism_validated_name = 'N/A'
        
        if stored_data is None:
            return dbc.Alert("Error connecting to g:Profiler API or receiving response.", color="danger"), True, go.Figure()

        if isinstance(stored_data, dict):
            enrichment_data_list = stored_data.get('results', [])
            gene_list = stored_data.get('gene_list', [])
            organism_code = stored_data.get('organism', 'hsapiens')
            
            organism_selected_name = organism_map.get(organism_code, organism_code)
            organism_validated_name = organism_map.get(organism_code, organism_code)
        
        
        genes_analyzed = len(gene_list)

        if not enrichment_data_list and not gene_list:
            return html.Div("Click 'Run g:Profiler Analysis' to display results.", className="text-muted text-center p-4"), True, go.Figure()

        
        df = pd.DataFrame(enrichment_data_list)
        
        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05
        
        if not (0 < val_threshold <= 1.0):
            val_threshold = 0.05
        
        
        filtered_df = df.copy()

        filtered_df = filtered_df[filtered_df['p_value'] < val_threshold]
        filter_message = f"Filtered results (P-Value corrected < {val_threshold})"
        
        
        df_plot = df[df['significant'] == True].copy() 
        
        manhattan_fig = create_gprofiler_manhattan_plot(df_plot, threshold_value)
        
        
        if not filtered_df.empty:
            display_df = filtered_df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False])
        else:
            display_df = pd.DataFrame() # Ensure display_df is always defined
        
        # Asegurarse de no mostrar 'intersection_genes' en la tabla
        if not display_df.empty:
             display_df = display_df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'source_order_display']].copy()
        
        
        # Construcción del Mensaje Resumen
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_validated_name}**"
        
        if not display_df.empty:
            pathways_message = f"Displaying **{len(display_df)}** terms. {filter_message}"
        else:
            pathways_message = f"No significant pathways found after applying the Gold Standard filter ({val_threshold})."
            
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        hidden_cols = ['source_order_display'] 

        display_columns = []
        for col in display_df.columns:
            is_hideable = True
            
            if col == 'p_value':
                column_config = {
                    'name': 'P-Value', 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.2e'}, 'hideable': is_hideable
                }
            elif col == 'intersection_size':
                column_config = {
                    'name': 'Genes\nMatched', 'id': col, 'type': 'numeric',
                    'hideable': is_hideable
                }
            elif col == 'term_size':
                column_config = {
                    'name': 'Term\nSize', 'id': col, 'type': 'numeric',
                    'hideable': is_hideable
                }
            elif col in ['precision', 'recall']:
                column_config = {
                    'name': col.capitalize(), 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.3f'},
                    'hideable': is_hideable
                }
            elif col == 'term_name':
                column_config = {
                    'name': 'Term Name', 'id': col, 'type': 'text',
                    'hideable': is_hideable
                }
            elif col == 'description':
                column_config = {
                    'name': 'Description', 'id': col, 'type': 'text',
                    'hideable': is_hideable
                }
            elif col == 'source':
                 column_config = {
                    'name': 'Source', 'id': col, 'type': 'text',
                    'hideable': is_hideable
                }
            elif col == 'source_order_display':
                column_config = {
                    'name': 'Source\nOrder', 
                    'id': col, 
                    'type': 'text',
                    'hideable': is_hideable
                }
            else:
                column_config = {'name': col.capitalize(), 'id': col, 'type': 'text', 'hideable': is_hideable}
            
            display_columns.append(column_config)
        
        results_content = [
            html.H4("g:Profiler Enrichment Results", className="mb-3"),
            
            html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="text-muted", style={'whiteSpace': 'pre-line'}),
            
            dash_table.DataTable(
                id='enrichment-results-table-gprofiler', 
                data=display_df.to_dict('records'),
                columns=display_columns,
                
                hidden_columns=hidden_cols, 
                
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=15,
                
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                
                style_cell_conditional=[
                    {'if': {'column_id': 'term_name'}, 'width': '15%', 'minWidth': '100px', 'textAlign': 'left'}, 
                    {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px', 'maxWidth': '350px', 'textAlign': 'left'},
                    {'if': {'column_id': 'source_order_display'}, 'width': '10%', 'minWidth': '60px', 'maxWidth': '80px', 'textAlign': 'center'}, 
                    {'if': {'column_id': 'p_value'}, 'width': '8%', 'minWidth': '70px', 'maxWidth': '80px', 'textAlign': 'center'},
                    {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'term_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'precision'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'recall'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'source'}, 'width': '7%', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
                ],
                
                style_cell={'padding': '8px', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'normal'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'whiteSpace': 'normal', 
                    'height': 'auto',
                    'padding': '10px 8px'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                tooltip_duration=None,
            )
        ]
        
        if not display_df.empty:
            return html.Div(results_content), False, manhattan_fig
        else:
            # Si display_df está vacía, mostrar el mensaje específico
            return html.Div(
                [
                    dbc.Alert([
                        html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="mb-0")
                    ], color="info", className="mt-3")
                ]
            ), False, manhattan_fig
        
    # 4.6. Callback para limpiar los resultados de g:Profiler (Mantenido)
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

    # logic/callbacks/enrichment_analysis.py (Reemplazar la función run_reactome_analysis)

    # 5. Callback para ejecutar el análisis de Reactome
    @app.callback(
        # CAMBIO CLAVE: DEFINICIÓN ORIGINAL (SIN allow_duplicate=True) 
        Output('reactome-results-store', 'data'), 
        Input('run-reactome-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        State('reactome-organism-input', 'value')], 
        prevent_initial_call=True
    )
    def run_reactome_analysis(n_clicks, selected_indices, items, organism_name):
        """Executes Reactome enrichment analysis and stores results."""
        if not n_clicks or not selected_indices:
            raise PreventUpdate

        # 1. Recolectar lista final de genes (Misma lógica que antes)
        combined_genes = set()
        for idx in selected_indices:
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

        if not gene_list:
            # Retornar diccionario con lista de resultados vacía
            return {'results': [], 'token': 'N/A', 'organism_used_api': 'N/A', 'organism_selected': organism_name, 'genes_analyzed': 0}

        # 2. Ejecutar servicio de Reactome
        service_response = ReactomeService.get_enrichment(gene_list, organism_name)

        if service_response is None:
            # Si hay error en API, devuelve un diccionario de error para que el store no sea None
            return {'results': [], 'token': 'ERROR', 'organism_used_api': 'N/A', 'organism_selected': organism_name, 'genes_analyzed': len(gene_list)}
        
        # 🔑 CLAVE: El service_response DEBE contener {token, results, organism_used_api, ...}
        # Aseguramos que la lista de genes analizados se adjunte.
        service_response['gene_list'] = gene_list
        
        return service_response

    @app.callback(
        [Output('reactome-results-content', 'children'),
         Output('clear-reactome-results-btn', 'disabled'),
         Output('reactome-diagram-output', 'children', allow_duplicate=True),
         Output('reactome-fireworks-output', 'children', allow_duplicate=True)], 
        Input('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def display_reactome_results(stored_data):
        
        placeholder_diagram = html.Div(
            dbc.Alert("Select a pathway from the table below to visualize the gene overlay.", color="secondary"), 
            className="p-3"
        )
        placeholder_fireworks = html.Div(
            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info"), 
            className="p-3"
        )
        
        if stored_data is None or not isinstance(stored_data, dict):
            raise PreventUpdate
        
        enrichment_data_list = stored_data.get('results', [])
        analysis_token = stored_data.get('token', 'N/A')
        organism_used_api = stored_data.get('organism_used_api', 'N/A')
        organism_selected = stored_data.get('organism_selected', 'N/A')
        gene_list = stored_data.get('gene_list', [])
        genes_analyzed = len(gene_list)
            
        
        fireworks_content = placeholder_fireworks
        if analysis_token and analysis_token != 'N/A' and organism_used_api and len(enrichment_data_list) > 0:
            organism_encoded = organism_used_api.replace(' ', '%20')
            fireworks_url = (
                f"https://reactome.org/PathwayBrowser/?species={organism_encoded}"
                f"#DTAB=AN&ANALYSIS={analysis_token}"
            )

            fireworks_content = html.Iframe(
                src=fireworks_url,
                style={"width": "100%", "height": "500px", "border": "none"},
                title=f"Reactome Pathway Browser/Fireworks visualization for {organism_used_api}"
            )

        
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_used_api}** | Analysis Token: **{analysis_token}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant Reactome pathways."
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        if not enrichment_data_list:
            simplified_no_results_message = f"No significant pathways found in Reactome.\n\n{input_message}"
            results_content = html.Div(
                [dbc.Alert([html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")], color="info", className="mt-3")]
            )
            
            df = pd.DataFrame()
            display_df = pd.DataFrame() 
            
            return results_content, False, placeholder_diagram, fireworks_content


        df = pd.DataFrame(enrichment_data_list)
        df = df.sort_values(by=['fdr_value', 'entities_found'], ascending=[True, False])
        display_df = df[['term_name', 'description', 'fdr_value', 'p_value', 'entities_found', 'entities_total']].copy()
        
        hidden_cols = ['description']
        display_columns = []
        for col in display_df.columns:
            if col == 'fdr_value':
                 column_config = {'name': 'FDR\n(Corrected P-Value)', 'id': col, 'type': 'numeric', 'format': {'specifier': '.2e'}, 'hideable': True}
            elif col == 'p_value':
                column_config = {'name': 'P-Value', 'id': col, 'type': 'numeric', 'format': {'specifier': '.2e'}, 'hideable': True}
            elif col == 'entities_found':
                column_config = {'name': 'Genes\nMatched', 'id': col, 'type': 'numeric', 'hideable': True}
            elif col == 'entities_total':
                column_config = {'name': 'Pathway\nSize', 'id': col, 'type': 'numeric', 'hideable': True}
            elif col == 'term_name':
                column_config = {'name': 'Pathway Name', 'id': col, 'type': 'text', 'hideable': True}
            elif col == 'description': 
                 column_config = {'name': 'ST_ID', 'id': col, 'type': 'text'}
            else:
                column_config = {'name': col.capitalize(), 'id': col, 'type': 'text', 'hideable': True}
            
            display_columns.append(column_config)

        results_content = [
            html.H4("Reactome Enrichment Results", className="mb-3"), 
            html.P(dcc.Markdown(summary_message_md, dangerously_allow_html=True), className="text-muted", style={'whiteSpace': 'pre-line'}),
            
            dash_table.DataTable(
                id='enrichment-results-table-reactome', 
                data=display_df.to_dict('records'), 
                columns=display_columns,
                hidden_columns=hidden_cols, 
                row_selectable='single', 
                selected_rows=[],
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=10,
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

    # logic/callbacks/enrichment_analysis.py (Añadir/Reemplazar el Callback 6)

    # 6. 🚀 CALLBACK DE VISUALIZACIÓN DEL DIAGRAMA COLOREADO
    @app.callback(
        Output('reactome-diagram-output', 'children', allow_duplicate=True),
        # Escuchar la SELECCIÓN de fila en la tabla
        Input('enrichment-results-table-reactome', 'selected_rows'),
        # Necesitar los datos brutos de la tabla para obtener el ST_ID
        State('enrichment-results-table-reactome', 'data'),
        # Necesitar el token para generar la URL coloreada
        State('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def visualize_reactome_diagram(selected_rows, table_data, stored_results):
        """Genera y muestra la imagen de la vía de Reactome con el overlay de genes."""

        if not selected_rows or not table_data:
            # Si no hay selección, o si la tabla aún no se carga
            raise PreventUpdate
        
        # 1. Extraer datos del Store de Resultados (Token)
        # Verificamos si el token existe y si no es un placeholder de error.
        if not stored_results or stored_results.get('token') in [None, 'N/A', 'ERROR'] or stored_results.get('token').startswith('REF_'):
            return html.Div(dbc.Alert("Analysis Token not available or invalid. Run the Reactome Analysis first.", color="warning"), className="p-3")

        analysis_token = stored_results['token']
        
        # 2. Obtener el Stable ID (ST_ID) de la vía seleccionada
        # selected_rows es una lista de índices de fila (page_current * page_size + index)
        selected_index = selected_rows[0]
        selected_pathway_data = table_data[selected_index]
        
        # El ST_ID (Stable ID) está en la columna 'description'
        pathway_st_id = selected_pathway_data.get('description')
        pathway_name = selected_pathway_data.get('term_name')

        if not pathway_st_id:
            return html.Div(dbc.Alert("Error: Could not find Pathway Stable ID (ST_ID).", color="danger"), className="p-3")

        # 3. Generar la URL de la Imagen Coloreada
        diagram_url = ReactomeService.get_diagram_url(
            pathway_st_id=pathway_st_id, 
            analysis_token=analysis_token,
            file_format="png" 
        )
        
        if diagram_url == "/assets/reactome_placeholder.png":
            return html.Div(dbc.Alert("Could not generate diagram URL (Token issue).", color="warning"), className="p-3")

        # 4. Renderizar la Imagen en Dash
        return html.Div([
            html.H5(f"Pathway Visualization: {pathway_name}", className="mt-3"),
            html.P(f"Stable ID: {pathway_st_id}", className="text-muted small"),
            html.A(
                html.Img(
                    src=diagram_url, 
                    alt=f"Reactome Diagram for {pathway_name} with gene overlay.",
                    style={'maxWidth': '100%', 'height': 'auto', 'border': '1px solid #ddd', 'borderRadius': '5px'}
                ),
                # Enlace para abrir el diagrama interactivo de Reactome en una nueva pestaña
                href=f"https://reactome.org/content/detail/{pathway_st_id}?analysis={analysis_token}",
                target="_blank",
                className="d-block mt-3"
            ),
            html.P(
                html.Strong("Click the image to view the interactive diagram on Reactome.org"), 
                className="text-center text-info small mt-2"
            )
        ], className="mt-4 p-3 border rounded shadow-sm")

    @app.callback(
        Output('reactome-results-store', 'data', allow_duplicate=True),
        Input('clear-reactome-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_reactome_results(n_clicks):
        if n_clicks and n_clicks > 0:
            return {'results': [], 'gene_list': [], 'organism': 'Homo sapiens'}
        raise PreventUpdate
            
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

        style_header_conditional = [] 
        style_data_conditional = base_style_data_conditional 
        
        return style_header_conditional, style_data_conditional
            
            
    # logic/callbacks/enrichment_analysis.py (Reemplazar la función display_gprofiler_clustergram)

    # 8. CALLBACK PARA EL HEATMAP/CLUSTERGRAM - VINCULADO AL THRESHOLD
    @app.callback(
        Output('gprofiler-clustergram-output', 'children'),
        [Input('gprofiler-results-store', 'data'),
        Input('gprofiler-threshold-input', 'value')], # 🔑 NUEVO INPUT
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def display_gprofiler_clustergram(stored_data, threshold_value, selected_indices, items):
        """
        Genera y muestra el Heatmap/Clustergram de Membresía Gen-Término, 
        vinculado al Threshold del Manhattan Plot.
        """
        
        # ... (Lógica de verificación de stored_data y recolección de genes se mantiene igual) ...

        # Convertir threshold_value a float para pasarlo al procesamiento
        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05 # Fallback

        # 2. Procesar datos (Obtiene la matriz Term x Gen y los contadores)
        # 🔑 PASAR EL THRESHOLD A LA FUNCIÓN DE PROCESAMIENTO 🔑
        heatmap_matrix, debug_counters = process_data_for_gene_term_heatmap(stored_data, threshold=val_threshold, max_terms=50) 
        
        # ... (El resto de la lógica de manejo de errores y retorno se mantiene igual) ...
        
        if heatmap_matrix.empty:
            # ... (Mensaje de error detallado se mantiene igual) ...
            # Aquí se debería incluir el threshold usado en el mensaje de error.
            
            detail_message = (
                f"**Filter Flow Debug (HEATMAP FAIL):**\n"
                f"... (Debugging info)\n"
                f"**Filter Used:** P-value < **{val_threshold}** (from Manhattan Plot input).\n"
                f"... (Resto de la lógica del mensaje de error) ..."
            )
            return dbc.Alert(...) # Retorno del mensaje de error

        # 4. Generar la figura del Heatmap
        heatmap_fig = create_gene_term_heatmap(heatmap_matrix)

        # 5. Retornar el dcc.Graph
        return dcc.Graph(
            figure=heatmap_fig, 
            config={'displayModeBar': True}
        )
