# logic/callbacks/enrichment_analysis.py (CÓDIGO COMPLETO Y CORREGIDO)

"""
Módulo de Callbacks para la Pestaña de Análisis de Enriquecimiento.
...
"""

# Importaciones estándar de Dash
import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# ... (todas las demás importaciones: pandas, json, etc. son las mismas)
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import logging
import numpy as np
import math 
import plotly.express as px
import plotly.graph_objects as go
# --- 🔑 IMPORTANTE: GProfilerService ahora se usa para validación Y enriquecimiento ---
from services.gprofiler_service import GProfilerService 
from services.reactome_service import ReactomeService 
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist, squareform

# Configuración del logger
logger = logging.getLogger(__name__)

# --- FUNCIÓN DE MANHATTAN PLOT (Sin cambios) ---
def create_gprofiler_manhattan_plot(df, threshold_value):
    # ... (código original de la función, líneas 46-180)
    """
    Genera una figura de Plotly (Manhattan plot) a partir de los resultados de g:Profiler.
    """
    # Define el umbral de significancia por defecto (para la línea roja)
    line_threshold_value = 0.05 
    try:
        # Intenta convertir el valor de entrada del usuario a un float
        float_threshold = float(threshold_value)
        # Valida que el umbral esté en un rango razonable
        if 0 < float_threshold <= 1.0:
            line_threshold_value = float_threshold
    except (TypeError, ValueError):
        # Si el valor no es válido (ej. texto), ignora y usa el defecto
        pass
    
    # Si no hay datos (DataFrame vacío), retorna una figura vacía con un mensaje
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant terms to display in the Manhattan Plot.", xaxis={'visible': False}, yaxis={'visible': False}, height=400)
        return fig
        
    # Calcula el valor -log10(p-value) para el eje Y.
    # 'clip' evita errores de log(0) asignando un valor mínimo muy pequeño.
    df['-log10(P-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    
    # --- Lógica de agrupación del Eje X ---
    # Queremos agrupar los términos por fuente (ej. GO:BP, KEGG) en el eje X.
    all_sources = df['source'].unique()
    # Separa las fuentes de Gene Ontology (GO) de las demás
    go_sources = sorted([s for s in all_sources if s.startswith('GO:')])
    other_sources = sorted([s for s in all_sources if not s.startswith('GO:')])
    # Define el orden final (GO primero, luego el resto)
    source_order = go_sources + other_sources

    # Aplica el orden de fuentes al DataFrame usando 'pd.Categorical'
    df['source'] = pd.Categorical(df['source'], categories=source_order, ordered=True)
    # Ordena los términos por fuente y luego por p-value (los más significativos primero)
    df = df.sort_values(['source', 'p_value'], ascending=True)
    # Asigna un índice numérico a cada término dentro de su grupo (para el eje X)
    df['term_index'] = df.groupby('source', observed=True).cumcount() + 1
    
    # Calcula el valor Y para la línea de umbral
    y_threshold = -np.log10(line_threshold_value)
    line_name = f"Gold Standard Threshold (P < {line_threshold_value:.4f})" 
    
    # Identifica los puntos "Gold Standard" (los que pasan el umbral)
    df['is_gold_standard'] = df['-log10(P-value)'] >= y_threshold
    # Asigna un grupo de color (Rojo para 'Gold', o el color de la fuente si no)
    df['plot_color_group'] = df.apply(lambda row: 'Gold' if row['is_gold_standard'] else row['source'], axis=1)
    
    # Define una paleta de colores para las fuentes
    source_colors = px.colors.qualitative.Bold
    # Mapea cada fuente única a un color
    source_color_map = {source: source_colors[i % len(source_colors)] for i, source in enumerate(df['source'].unique())}
    # Mapa de color final (fuerza el 'Gold' a ser rojo)
    color_map = {'Gold': 'red'} 
    for source, color in source_color_map.items():
        color_map[source] = color 

    # --- Lógica de Tamaño de Marcador ---
    # El tamaño del punto representará el 'intersection_size' (cuántos genes coinciden)
    min_size = 5
    max_size = 40 
    max_val = df['intersection_size'].max()
    
    if max_val == 0:
        df['marker_size'] = min_size
    else:
        # Escala linealmente el tamaño del marcador entre min_size y max_size
        df['marker_size'] = (df['intersection_size'].clip(lower=0) * (max_size - min_size) / max_val) + min_size
        
    df['marker_size'] = df['marker_size'].clip(upper=max_size)
    
    df_plot = df.copy().reset_index(drop=True)

    if df_plot.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant terms found to plot.", xaxis={'visible': False}, yaxis={'visible': False}, height=400)
        return fig
    
    # Creación del gráfico de dispersión (scatter plot)
    fig = px.scatter(
        df_plot, 
        x='term_index',                     # Posición X (índice numérico)
        y='-log10(P-value)',                # Posición Y (significancia)
        color='plot_color_group',           # Color (Rojo o por fuente)
        color_discrete_map=color_map,       # Mapa de colores definido
        size='marker_size',                 # Tamaño del punto
        # Datos extra para mostrar en el hover (tooltip)
        custom_data=['term_name', 'p_value', 'intersection_size', 'source', 'is_gold_standard'],
        hover_data={'term_index': False, '-log10(P-value)': ':.2f', 'term_name': True, 'p_value': ':.2e', 'intersection_size': True, 'source': True, 'is_gold_standard': True}
    )
    
    # --- Lógica de Etiquetas del Eje X ---
    # Calcula el punto central de cada grupo de fuente para poner la etiqueta
    source_labels = df_plot.groupby('source', observed=True)['term_index'].agg(['min', 'max']).reset_index() 
    source_labels['center'] = (source_labels['min'] + source_labels['max']) / 2
    
    # Configuración final del layout del gráfico
    fig.update_layout(
        # Asigna las etiquetas de texto (KEGG, REAC, etc.) a las posiciones centrales
        xaxis={'title': "Functional Enrichment Terms (Grouped by Source)", 'tickmode': 'array', 'tickvals': source_labels['center'], 'ticktext': source_labels['source'], 'showgrid': False, 'zeroline': False, 'tickangle': 0},
        yaxis={'title': '-log10(P-value)', 'automargin': True},
        showlegend=True,
        height=550,
        margin={'t': 30, 'b': 80, 'l': 50, 'r': 10}, 
        plot_bgcolor='white'
    )

    # Añade la línea roja punteada del umbral de significancia
    fig.add_hline(y=y_threshold, line_dash="dot", line_color="red", annotation_text=line_name, annotation_position="top right")

    # Define la plantilla del tooltip (hovertemplate) para mostrar la info personalizada
    fig.update_traces(
        marker=dict(opacity=0.6, line=dict(width=0.5, color='DarkSlateGrey')),
        hovertemplate="<b>Term:</b> %{customdata[0]}<br><b>Source:</b> %{customdata[3]}<br><b>-log10(P-value):</b> %{y:.2f}<br><b>P-value:</b> %{customdata[1]:.2e}<br><b>Genes Matched:</b> %{customdata[2]}<br><b>Gold Standard:</b> %{customdata[4]}<br><extra></extra>"
    )
    return fig


# --- FUNCIÓN DE PROCESAMIENTO DE HEATMAP (Sin cambios) ---
def process_data_for_gene_term_heatmap(stored_data, threshold=0.05, max_terms=50):
    # ... (código original de la función, líneas 183-259)
    """
    Procesa los datos del store para crear la matriz de datos del heatmap.
    Filtra por p-value, toma el top N, y pivotea los datos (Términos vs Genes).
    """
    # Extrae los resultados y la lista de genes validados del store
    results = stored_data.get('results', [])
    gene_list_validated = stored_data.get('gene_list_validated', []) 
    
    # Contadores de depuración (pueden ser útiles)
    debug_counters = {
        'timestamp_start': datetime.now().strftime("%H:%M:%S.%f"), 'initial_terms': len(results), 'initial_genes': len(gene_list_validated), 'terms_after_pvalue_filter': 0,
        'terms_before_zerovariance_clean': 0, 'genes_before_zerovariance_clean': 0, 'terms_removed_by_zerovariance': 0, 'genes_removed_by_zerovariance': 0, 'timestamp_end': None
    }
    
    # Si no hay resultados o no hay genes, retorna una matriz vacía
    if not results or not gene_list_validated:
        return pd.DataFrame(), debug_counters

    # Convierte la lista de resultados en un DataFrame de Pandas
    df = pd.DataFrame(results)

    # Manejo de caso borde: si el DataFrame está vacío (ej. error de API)
    if df.empty:
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    # Calcula el -log10(p-value) para usarlo como valor 'Z' en el heatmap
    df['-log10(q-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    # Filtra por el umbral de p-value, ordena, y toma los 'max_terms' más significativos
    df_significant = df[df['p_value'] < threshold].sort_values(by='p_value', ascending=True).head(max_terms) 
    
    debug_counters['terms_after_pvalue_filter'] = len(df_significant)
    
    # Si ningún término pasa el filtro, retorna una matriz vacía
    if df_significant.empty:
        debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
        return pd.DataFrame(), debug_counters

    # Lista de términos (filas) y genes (columnas) para la matriz
    term_list = df_significant['term_name'].tolist()
    # Crea la matriz vacía (llena de 0.0) con las dimensiones correctas
    heatmap_matrix = pd.DataFrame(0.0, index=term_list, columns=gene_list_validated)
    
    # Itera sobre los términos significativos para poblar la matriz
    for _, row in df_significant.iterrows():
        term_name = row['term_name']
        log_q_value = row['-log10(q-value)'] 
        # Obtiene la lista de genes que intersectan para este término
        raw_intersecting_genes = row.get('intersection_genes', [])
        
        # Pobla la matriz: si un gen intersecta con un término,
        # pone el valor -log10(q-value) en la celda [término, gen]
        for gene in raw_intersecting_genes:
            if gene in gene_list_validated:
                heatmap_matrix.loc[term_name, gene] = log_q_value
                
    debug_counters['terms_before_zerovariance_clean'] = heatmap_matrix.shape[0]
    debug_counters['genes_before_zerovariance_clean'] = heatmap_matrix.shape[1]

    # --- Filtro de Varianza Cero ---
    # Elimina filas (términos) que no tengan ninguna coincidencia de gen
    heatmap_matrix = heatmap_matrix.loc[(heatmap_matrix != 0).any(axis=1)]
    # Elimina columnas (genes) que no coincidan con ningún término
    heatmap_matrix = heatmap_matrix.loc[:, (heatmap_matrix != 0).any(axis=0)]
    
    debug_counters['terms_removed_by_zerovariance'] = debug_counters['terms_before_zerovariance_clean'] - heatmap_matrix.shape[0]
    debug_counters['genes_removed_by_zerovariance'] = debug_counters['genes_before_zerovariance_clean'] - heatmap_matrix.shape[1]
    debug_counters['timestamp_end'] = datetime.now().strftime("%H:%M:%S.%f")
                
    # Retorna la matriz procesada y los contadores
    return heatmap_matrix, debug_counters


# --- FUNCIÓN DE CREACIÓN DE HEATMAP (Sin cambios) ---
def create_gene_term_heatmap(heatmap_matrix):
    # ... (código original de la función, líneas 262-337)
    """
    Genera la figura Plotly (clustergram/heatmap) a partir de la matriz procesada.
    """
    # Si la matriz está vacía después del filtro, retorna una figura vacía
    if heatmap_matrix.empty:
        fig = go.Figure()
        fig.update_layout(title="No significant gene-term associations remain after filtering.", height=400)
        return fig
    
    # El clustering solo se puede hacer si hay al menos 2 filas y 2 columnas
    perform_row_clustering = heatmap_matrix.shape[0] >= 2
    perform_col_clustering = heatmap_matrix.shape[1] >= 2
    
    clustered_matrix = heatmap_matrix.copy()
    clustering_successful = True
    
    try:
        # Si es posible, realiza el clustering jerárquico de filas
        if perform_row_clustering:
            # Calcula la distancia (correlación) entre filas
            row_linkage = sch.linkage(pdist(clustered_matrix, metric='correlation'), method='average')
            # Obtiene el orden de las filas (hojas del dendrograma)
            row_order_indices = sch.dendrogram(row_linkage, orientation='right', no_plot=True)['leaves']
            # Reordena la matriz según el clustering
            clustered_matrix = clustered_matrix.iloc[row_order_indices, :]
        
        # Si es posible, realiza el clustering jerárquico de columnas
        if perform_col_clustering:
            # Calcula la distancia (correlación) entre columnas (transpuesta)
            col_linkage = sch.linkage(pdist(clustered_matrix.T, metric='correlation'), method='average')
            # Obtiene el orden de las columnas
            col_order_indices = sch.dendrogram(col_linkage, orientation='top', no_plot=True)['leaves']
            # Reordena la matriz según el clustering
            clustered_matrix = clustered_matrix.iloc[:, col_order_indices]
            
    except ValueError as e:
        # Manejo de error si el clustering falla (ej. datos insuficientes)
        logger.error(f"Clustering failed: {e}. Plotting without clustering.")
        clustered_matrix = heatmap_matrix.copy()
        clustering_successful = False

    # Define la escala de colores (Z)
    z_max = clustered_matrix.values.max()
    z_min = 0.0 
    colormap = px.colors.sequential.Plasma
    # Crea una matriz de 'Sí'/'No' para el tooltip (membresía)
    member_matrix = np.where(clustered_matrix.values > 0, "Sí", "No")
    
    # Crea la figura Heatmap de Plotly
    fig = go.Figure(data=go.Heatmap(
        z=clustered_matrix.values,        # Valores (color)
        x=clustered_matrix.columns,       # Eje X (genes)
        y=clustered_matrix.index,         # Eje Y (términos)
        colorscale=colormap,
        zmin=z_min,
        zmax=z_max,
        showscale=True,
        colorbar=dict(title=dict(text='-log10(q-value)', side='right'), thickness=15, len=0.7),
        customdata=member_matrix,         # Datos de membresía para el tooltip
        hovertemplate="<b>Term:</b> %{y}<br><b>Gene:</b> %{x}<br><b>-log10(p-value):</b> %{z:.2f}<br><b>Membresía:</b> %{customdata} <br><extra></extra>"
    ))

    # Genera un título dinámico basado en el éxito del clustering
    status_parts = []
    if clustering_successful and perform_row_clustering and perform_col_clustering:
        status_parts.append("Clustered Successfully")
    else:
        status_parts.append("Not Clustered")
    if not perform_row_clustering or not perform_col_clustering:
         status_parts.append("(Low Dimension)")
    clustering_status = " ".join(status_parts)

    # Configuración final del layout del heatmap
    fig.update_layout(
        title=f"Functional Clustergram (Term vs. Gene Membership) - {clustering_status}",
        xaxis_title="Genes de Entrada",
        yaxis_title="Términos Enriquecidos",
        xaxis={'tickangle': 90, 'showgrid': False, 'zeroline': False},
        yaxis={'showgrid': False, 'zeroline': False, 'automargin': True},
        # Altura dinámica, con un mínimo de 500 y máximo de 1000
        height=min(max(50 * clustered_matrix.shape[0], 500), 1000),
        margin=dict(l=250, r=20, t=50, b=100) # Margen izquierdo amplio para los nombres de términos
    )
    return fig


# --- REGISTRO DE CALLBACKS ---
def register_enrichment_callbacks(app): 
    """
    Registra todos los callbacks de la pestaña de enriquecimiento en la app principal.
    """
    
    # 1. Callback de Actualización de IDs y Trigger (Sin cambios)
    @app.callback(
        [Output('enrichment-selected-item-ids-store', 'data', allow_duplicate=True),
         Output('enrichment-render-trigger-store', 'data', allow_duplicate=True)],
        [Input('interest-panel-store', 'data'),
         Input('enrichment-selected-indices-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=True 
    )
    def update_selected_items_and_render_trigger(items, selected_indices_list, active_tab):
        # ... (código original, líneas 356-373)
        """
        Este callback "escucha" cambios en el panel de interés o en la selección,
        y actualiza un 'trigger' (enrichment-render-trigger-store).
        Esto fuerza el re-renderizado del selector visual (callback 1.5)
        solo cuando la pestaña de enriquecimiento está visible.
        """
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Si cambia el panel, la selección, O si el usuario navega a la pestaña de enriquecimiento
        if trigger_id in ['interest-panel-store', 'enrichment-selected-indices-store'] or (trigger_id == 'main-tabs' and active_tab == 'enrichment-tab'):
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            # Actualiza el trigger con un timestamp para asegurar que se dispare
            return selected_item_ids, datetime.now().timestamp()
        
        raise PreventUpdate


    # 1.5. Callback de Renderizado Real (Sin cambios)
    @app.callback(
        Output('enrichment-visual-selector', 'children'),
        Input('enrichment-render-trigger-store', 'data'), # Disparado por el callback anterior
        [State('interest-panel-store', 'data'),
         State('enrichment-selected-indices-store', 'data'),
         State('main-tabs', 'active_tab'),
         State('data-store', 'data')]
    )
    def render_visual_enrichment_selector(trigger_data, items, selected_indices_list, active_tab, data_store):
        # ... (código original, líneas 385-431)
        """
        Construye las "tarjetas" (cards) visuales de selección de ítems
        (soluciones, grupos de genes) en la pestaña de enriquecimiento.
        """
        # No hagas nada si la pestaña no está activa
        if active_tab != 'enrichment-tab':
             raise PreventUpdate 

        if not items:
            return html.P("No items available. Add solutions, genes, or gene groups to your Interest Panel first.",
                         className="text-muted text-center py-4")

        # Carga el diccionario de soluciones para obtener genes si es necesario
        all_solutions_dict = {}
        if data_store:
            for front in data_store.get("fronts", []):
                for sol in front["data"]:
                    all_solutions_dict[sol['solution_id']] = sol

        cards = []
        # Itera sobre los ítems del panel de interés
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', '')
            item_comment = item.get('comment', '')

            # Omite ítems que no sean relevantes para el análisis de genes
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue
            
            # Lógica para mostrar la información correcta en la tarjeta
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

            # Marca la tarjeta como seleccionada si su índice está en la lista
            is_selected = [idx] if idx in selected_indices_list else []
            
            # Construye el componente de tarjeta (Card)
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


    # 2. Callback de selección (Sin cambios)
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input({'type': 'enrichment-card-checkbox', 'index': ALL}, 'value'), # Se activa al hacer clic en cualquier switch
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def update_enrichment_selection(list_of_checkbox_values, items):
        """
        Se activa cuando el usuario (des)selecciona una tarjeta.
        Actualiza el store de selección y recalcula la lista combinada de genes (sucios).
        """
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

        # Esta es la lista "sucia" (puede contener probes)
        gene_count = len(combined_genes)
        
        # Prepara el string de genes (separado por espacios)
        gene_string = ""
        if combined_genes:
            cleaned_genes = {g for g in combined_genes if g and isinstance(g, str)}
            if cleaned_genes:
                gene_string = " ".join(sorted(list(cleaned_genes)))
        
        
        # Muestra un panel de resumen con el conteo total de IDs únicos
        summary_panel = dbc.Alert([
            html.H6("Combined Input IDs for Analysis (Input Set)", className="alert-heading"),
            html.P(f"Total Unique IDs (Probes/Genes): {gene_count}", className="mb-1"),
            html.P(f"Source Items: {len(selected_indices_list)}", className="mb-0"),
            
            # Estructura del botón de copia (sin cambios)
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
    
    
    # 2.5. Callback de limpiar selección (Sin cambios)
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input('clear-enrichment-selection-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_enrichment_selection(n_clicks):
        # ... (código original, líneas 480-488)
        """
        Resetea la selección al hacer clic en el botón 'Clear Selection'.
        """
        if n_clicks and n_clicks > 0:
            # Retorna una lista vacía de índices y el mensaje de 'No items'
            return [], html.Div(dbc.Alert("No items selected. Select items above to view the combined gene list.", color="info", className="mt-3"))
        raise PreventUpdate

    
    # 2.6. Visibilidad del botón Clear (Sin cambios)
    @app.callback(
        Output('clear-enrichment-btn-container', 'style'),
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_clear_selection_button(selected_indices):
        # ... (código original, líneas 491-499)
        """
        Muestra u oculta el botón 'Clear Selection' basado en si hay ítems seleccionados.
        """
        if selected_indices and len(selected_indices) > 0:
            return {'display': 'block'}
        return {'display': 'none'}


    # 3. Habilitar botones de análisis (Sin cambios)
    @app.callback(
        [Output('run-gprofiler-btn', 'disabled'),
         Output('run-reactome-btn', 'disabled')], 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices):
        # ... (código original, líneas 505-512)
        """
        Habilita o deshabilita los botones de 'Run Analysis' si hay al menos un ítem seleccionado.
        """
        is_disabled = not (selected_indices and len(selected_indices) > 0)
        return is_disabled, is_disabled
  
    
    # 4. Ejecutar g:Profiler (MODIFICADO: Con Selector de Namespace y Switch)
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         Output('gprofiler-spinner-output', 'children')], 
        Input('run-gprofiler-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('gprofiler-organism-dropdown', 'value'),
         State('gprofiler-sources-checklist', 'value'),
         # NUEVOS ESTADOS
         State('gprofiler-target-namespace', 'value'),
         State('gprofiler-validation-switch', 'value')],
        prevent_initial_call=True
    )
    def run_gprofiler_analysis(n_clicks, selected_indices, items, organism, selected_sources, target_namespace, use_validation):
        if not n_clicks or not selected_indices:
            raise PreventUpdate
        
        # 1. Recolección (Genes "Sucios")
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

        # 2. Lógica Condicional: Validación/Traducción vs Raw
        clean_gene_list = []
        
        if use_validation:
            # Opción A: Usar g:Convert con el Namespace seleccionado
            # Nota: Pasamos target_namespace (ej. 'HGNC', 'ENSG')
            validation_response = GProfilerService.validate_genes(gene_list_to_validate, organism, target_namespace=target_namespace)
            clean_gene_list = validation_response.get('validated_genes', [])
        else:
            # Opción B: Usar la lista cruda tal cual
            clean_gene_list = sorted(list(set(gene_list_to_validate)))
        
        if not clean_gene_list:
            return {'results': [], 'gene_list_validated': [], 'gene_list_original_count': gene_list_original_count, 'organism': organism}, None

        # 3. Análisis
        full_response = GProfilerService.get_enrichment(clean_gene_list, organism, selected_sources)

        if full_response is None:
            return {'results': None, 'gene_list_validated': clean_gene_list, 'gene_list_original_count': gene_list_original_count, 'organism': organism}, None 

        # 4. Procesamiento (Igual que antes)
        enrichment_data_list = full_response.get('result', [])
        metadata = full_response.get('meta', {})
        
        # Intentar mapear IDs de vuelta si es necesario (Lógica compleja de mapeo se mantiene igual)
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
            
            # Si no hubo validación, a veces el mapeo de intersección directo es más seguro
            # Si se usó validación, usamos la lógica de mapeo de g:Profiler
            
            if not mapped_ensg_list and not use_validation:
                # Fallback simple para modo RAW: no podemos garantizar qué genes intersectan exactamente 
                # sin el mapeo de ENSG, pero g:Profiler a veces devuelve los nombres directos si coinciden.
                # (Esta parte es compleja porque g:Profiler siempre devuelve ENSG en intersecciones)
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

    # 4.5. Mostrar resultados g:Profiler (MODIFICADO: UI Limpia)
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

        # Dataframes y Figuras
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
        
        # --- UI RESUMEN (MODIFICADA) ---
        input_message = f"**Input:** Total Probes/IDs: **{gene_list_original_count}** | Selected Organism: **{organism_selected_name}**"
        
        # Eliminado: " | Unrecognized/Discarded: X"
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
        
        # Eliminado: unrecognized_report (Alerta con Details de genes no reconocidos)

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
            # Eliminado: unrecognized_report if unrecognized_report else None,
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
         # NUEVOS ESTADOS
         State('reactome-target-namespace', 'value'),
         State('reactome-validation-switch', 'value')],
        prevent_initial_call=True
    )
    def manage_reactome_analysis(run_clicks, clear_clicks, selected_indices, items, organism_name, selected_options, target_namespace, use_validation):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # --- CASO 1: CLEAR ---
        if trigger_id == 'clear-reactome-results-btn':
            return {
                'results': [], 
                'gene_list_original': [], 
                'gene_list_validated': [], 
                'organism_selected': 'Homo sapiens'
            }, None

        # --- CASO 2: RUN ---
        if trigger_id == 'run-reactome-btn':
            if not selected_indices:
                raise PreventUpdate
            
            options = selected_options or []
            projection = 'projection' in options
            include_disease = 'disease' in options
            interactors = 'interactors' in options
            
            # 1. Recolección
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
            
            # 2. Validación / Preparación
            clean = []
            if use_validation:
                # Usamos GProfilerService para convertir a UNIPROT/ENSG antes de enviar a Reactome
                # Reactome suele requerir mapping a 'hsapiens' para la conversión correcta si el target es UNIPROT
                val_res = GProfilerService.validate_genes(raw, 'hsapiens', target_namespace=target_namespace)
                clean = val_res.get('validated_genes', [])
            else:
                # Modo Raw: Enviamos tal cual
                clean = sorted(list(set(raw)))
            
            store = {'results': [], 'token': 'ERROR', 'gene_list_validated': clean, 'gene_list_original': raw}
            
            if not clean: 
                return store, None
            
            # 3. Análisis
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

    # 5.5 Mostrar resultados Reactome (MODIFICADO: UI Limpia)
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
        
        # --- UI RESUMEN (MODIFICADA) ---
        input_message = f"**Input:** Total Probes/IDs: **{genes_original_count}** | Selected Organism: **{organism_selected}**"
        
        # Eliminado: " | Unrecognized/Discarded: X"
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

        # Tabla Reactome (Sin cambios visuales grandes)
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

    # 6. Visualizar Diagrama Reactome (Sin cambios)
    @app.callback(
        [Output('reactome-diagram-output', 'children', allow_duplicate=True),
         Output('reactome-diagram-spinner-output', 'children')], 
        Input('enrichment-results-table-reactome', 'selected_rows'), # Se activa al seleccionar una fila
        State('enrichment-results-table-reactome', 'data'),
        State('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def visualize_reactome_diagram(selected_rows, table_data, stored_results):
        # ... (código original, líneas 1028-1077)
        """
        Muestra la imagen del diagrama de pathway para la fila seleccionada en la tabla.
        """
        if not selected_rows or not table_data:
            raise PreventUpdate
        
        placeholder_alert = html.Div(dbc.Alert("Select a pathway from the table to visualize gene overlap.", color="secondary"), className="p-3")

        # No se puede mostrar el diagrama si no hay un token de análisis válido
        if not stored_results or stored_results.get('token') in [None, 'N/A', 'ERROR'] or stored_results.get('token').startswith('REF_'):
            return placeholder_alert, None

        analysis_token = stored_results['token']
        selected_index = selected_rows[0]
        selected_pathway_data = table_data[selected_index]
        # 'description' contiene el ST_ID
        pathway_st_id = selected_pathway_data.get('description')
        pathway_name = selected_pathway_data.get('term_name')

        if not pathway_st_id:
            return html.Div(dbc.Alert("Error: Could not find Pathway Stable ID (ST_ID).", color="danger"), className="p-3"), None
        
        # Llama al servicio para obtener la imagen del diagrama (en base64)
        image_base64_string = ReactomeService.get_diagram_image_base64(
            pathway_st_id=pathway_st_id, 
            analysis_token=analysis_token
        )
        
        if image_base64_string is None:
            return html.Div(dbc.Alert("Error: Could not download the pathway diagram from Reactome.", color="danger"), className="p-3"), None

        # Muestra la imagen (como string base64) y un enlace interactivo
        diagram_content = html.Div([
            html.H5(f"Pathway Visualization: {pathway_name}", className="mt-3"),
            html.P(f"Stable ID: {pathway_st_id}", className="text-muted small"),
            html.A(
                html.Img(
                    src=image_base64_string, 
                    alt=f"Reactome Diagram for {pathway_name}", 
                    style={'maxWidth': '100%', 'height': 'auto', 'border': '1px solid #ddd', 'borderRadius': '5px'}
                ),
                # El enlace lleva al visualizador interactivo de Reactome
                href=f"https://reactome.org/content/detail/{pathway_st_id}?analysis={analysis_token}",
                target="_blank",
                className="d-block mt-3"
            ),
            html.P(html.Strong("Click the image to view the interactive diagram on Reactome.org"), className="text-center text-info small mt-2")
        ], className="mt-4 p-3 border rounded shadow-sm")
        
        return diagram_content, None


    clear_reactome_results
            
            
    # 7.5. Ajuste de tabla (Sin cambios)
    @app.callback(
        [Output('enrichment-results-table-gprofiler', 'style_header_conditional', allow_duplicate=True),
        Output('enrichment-results-table-gprofiler', 'style_data_conditional', allow_duplicate=True)],
        Input('enrichment-results-table-gprofiler', 'columns'),
        State('enrichment-results-table-gprofiler', 'style_data_conditional'),
        prevent_initial_call=True
    )
    def adjust_gprofiler_column_widths_dynamically(current_columns, base_style_data_conditional):
        # ... (código original, líneas 1090-1100)
        """
        Callback auxiliar para ajustes dinámicos de la tabla (si es necesario).
        """
        if current_columns is None:
            raise PreventUpdate
        return [], base_style_data_conditional
            
            
    # 8. Callback para Heatmap (Sin cambios)
    @app.callback(
        Output('gprofiler-clustergram-output', 'children'),
        [Input('gprofiler-results-store', 'data'),      # Se activa cuando cambian los resultados
        Input('gprofiler-threshold-input', 'value')], # O cuando cambia el umbral
        [State('enrichment-selected-indices-store', 'data'),
        State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def display_gprofiler_clustergram(stored_data, threshold_value, selected_indices, items):
        """
        Renderiza el clustergram (heatmap) basado en los resultados de g:Profiler.
        """

        # --- 💡 Guarda (sin cambios) 💡 ---
        if not stored_data or isinstance(stored_data, list):
            return dbc.Alert(
                "Ejecute un análisis de g:Profiler para generar el clustergram.",
                color="info",
                className="mt-3"
            )
        # --- 💡 Fin de la Guarda 💡 ---

        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05 

        # Llama a la función de procesamiento para obtener la matriz de datos
        # (Esta función usa 'gene_list_validated' del store, que ahora es la lista limpia)
        heatmap_matrix, debug_counters = process_data_for_gene_term_heatmap(stored_data, threshold=val_threshold, max_terms=50) 
        
        # Si la matriz está vacía, muestra un mensaje de información detallado
        if heatmap_matrix.empty:
            if not stored_data or (stored_data.get('results') is None):
                 detail_message = "No analysis data found. Run g:Profiler analysis first."
            # Mensaje clave: si no hay genes validados (limpios)
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

        # Si hay datos, genera la figura del heatmap
        heatmap_fig = create_gene_term_heatmap(heatmap_matrix)

        # Retorna el gráfico
        return dcc.Graph(figure=heatmap_fig, config={'displayModeBar': True})