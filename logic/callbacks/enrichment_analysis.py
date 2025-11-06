# logic/callbacks/enrichment_analysis.py (CÓDIGO COMPLETO FINAL CON TAMAÑO DINÁMICO)

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
import math # Importar math para manejar la validación de log

import plotly.express as px
import plotly.graph_objects as go

# Importamos AMBOS servicios
from services.gprofiler_service import GProfilerService 
from services.reactome_service import ReactomeService 

logger = logging.getLogger(__name__)

def create_gprofiler_manhattan_plot(df, threshold_value):
    """
    Crea un Manhattan Plot para los resultados de g:Profiler.
    El 'Gold Standard' es la línea de umbral.
    """
    
    # 1. Validación Robusta y Asignación de Valor de Línea
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
        
    # Crear la columna -log10(p_value)
    df['-log10(P-value)'] = -1 * np.log10(df['p_value'].clip(lower=1e-300))
    
    # 1. Preparar el DataFrame para la visualización del Manhattan Plot (Eje X)
    source_order = ['GO:BP', 'GO:MF', 'GO:CC', 'KEGG', 'REAC']
    df['source'] = pd.Categorical(df['source'], categories=source_order, ordered=True)
    df = df.sort_values(['source', 'p_value'], ascending=[True, True])
    
    # Asignar una posición secuencial dentro de cada fuente
    df['term_index'] = df.groupby('source', observed=True).cumcount() + 1
    
    # 2. Definir el Umbral (Eje Y) y el Coloreado Gold Standard
    y_threshold = -np.log10(line_threshold_value)
    line_name = f"Gold Standard Threshold (P < {line_threshold_value:.4f})" 
    
    # COLOREADO GOLD STANDARD
    df['is_gold_standard'] = df['-log10(P-value)'] >= y_threshold
    df['plot_color_group'] = df.apply(
        lambda row: 'Gold' if row['is_gold_standard'] else row['source'], axis=1
    )
    
    # Definir mapa de colores
    source_colors = px.colors.qualitative.Bold
    source_color_map = {source: source_colors[i % len(source_colors)] for i, source in enumerate(df['source'].unique())}
    color_map = {'Gold': 'red'} 
    for source, color in source_color_map.items():
        color_map[source] = color 


    # 3. Lógica de Tamaño (Escala de Raíz Cuadrada)
    min_size = 5
    max_size = 40 
    
    # 🔑 CAMBIO CLAVE: Usamos el valor máximo (sin raíz cuadrada) para escala lineal
    max_val = df['intersection_size'].max()
    
    # --- DEBUG: MARCADO DE TAMAÑO DE BURBUJA ---
    logger.info(f"DEBUG SIZE: Max Intersection Size found (Global): {df['intersection_size'].max()}")
    logger.info(f"DEBUG SIZE: Scaling Function: LINEAR (Proportional to Intersection)")
    logger.info(f"DEBUG SIZE: Scaling Range: {min_size} to {max_size}")
    logger.info(f"DEBUG SIZE: Max Value for Normalization: {max_val}") # Actualizado el log
    
    if max_val == 0:
        df['marker_size'] = min_size
    else:
        # Calcular el tamaño del marcador en el DataFrame completo (Fórmula Lineal)
        df['marker_size'] = (
            df['intersection_size'].clip(lower=0) * (max_size - min_size) / max_val
        ) + min_size
        
    df['marker_size'] = df['marker_size'].clip(upper=max_size)
    
    # DEBUG ADICIONAL: Mostrar un top 5 de ejemplos de escalado (antes de filtrar por significant=True)
    debug_sample = df.sort_values('intersection_size', ascending=False).head(5)
    for index, row in debug_sample.iterrows():
        logger.info(
            f"DEBUG SIZE SAMPLE: Source={row['source']}, Intersection={row['intersection_size']}, "
            f"P_Value={row['p_value']:.2e}, Calculated Size={row['marker_size']:.2f}"
        )


    # 4. Generación del Manhattan Plot
    # Creamos df_plot que contendrá solo los puntos significativos
    df_plot = df[df['significant'] == True].copy() 
    
    # 🔑 SOLUCIÓN CRÍTICA: Resetear el índice para sincronizar el array de tamaño 🔑
    df_plot = df_plot.reset_index(drop=True) 

    
    if df_plot.empty:
        # Si no hay puntos significativos para dibujar, devolvemos una figura vacía con mensaje.
        fig = go.Figure()
        fig.update_layout(
            title="No significant terms found to plot.",
            xaxis={'visible': False},
            yaxis={'visible': False},
            height=400
        )
        return fig
        
    
    # 🔑 CORRECCIÓN: Pasar 'marker_size' a Plotly Express para asegurar la sincronización 🔑
    fig = px.scatter(
        df_plot, # Usamos df_plot filtrado
        x='term_index',
        y='-log10(P-value)',
        color='plot_color_group',
        color_discrete_map=color_map,
        size='marker_size', # 🔑 CLAVE: Plotly Express ahora enlaza la columna de tamaño 🔑
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
    
    # 5. Configurar el eje X y las líneas divisorias 
    source_labels = df_plot.groupby('source', observed=True)['term_index'].agg(['min', 'max']).reset_index() 
    source_labels['center'] = (source_labels['min'] + source_labels['max']) / 2
    
    # 5. Configurar el eje X y las líneas divisorias 
    # ... (cálculo de source_labels['center'] se mantiene igual)

    fig.update_layout(
        xaxis={
            'title': "Functional Enrichment Terms (Grouped by Source)",
            'tickmode': 'array',
            'tickvals': source_labels['center'], 
            'ticktext': source_labels['source'], 
            'showgrid': False,
            'zeroline': False,
            'tickangle': 0 # Asegura tick horizontal para etiquetas cortas
        },
        yaxis={
            'title': '-log10(P-value)',
            'automargin': True
        },
        # ... (configuración de líneas divisorias se mantiene igual)
        showlegend=True,
        height=550,
        margin={'t': 30, 'b': 80, 'l': 50, 'r': 10}, # CLAVE: Aumentado de 50 a 80
        plot_bgcolor='white'
    )

    # 6. Agregar la línea de umbral (Gold Standard)
    fig.add_hline(
        y=y_threshold, 
        line_dash="dot", 
        line_color="red", 
        annotation_text=line_name, 
        annotation_position="top right"
    )

    # 7. Configurar el Tooltip y el TAMAÑO DEL MARCADOR (Usando la columna ya sincronizada)
    fig.update_traces(
        marker=dict(
            # 🔑 ELIMINADO: Se eliminó la línea 'size=df_plot['marker_size']' aquí,
            # ya que el tamaño fue especificado en px.scatter arriba.
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
        
        # If interest panel changed, always trigger render (even if tab is not active)
        if trigger_id == 'interest-panel-store':
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        # If tab changed to enrichment tab, trigger render
        if trigger_id == 'main-tabs' and active_tab == 'enrichment-tab':
            selected_item_ids = []
            if items:
                for idx, item in enumerate(items):
                    if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                        selected_item_ids.append(item.get('id', str(idx)))
            return selected_item_ids, datetime.now().timestamp()
        
        # If selection indices changed while on enrichment tab, trigger render
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

        # Preparar diccionario de soluciones para fallback (tomado de gene_groups_analysis.py)
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

            # 🔑 Lógica de creación de tarjeta 🔑
            
            # Crear badge e ícono
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
            
            # Crear la tarjeta visualmente (el HTML)
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                # 🔑 ID: Usamos 'enrichment-card-checkbox' como ID de tipo
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
        # Si no hay trigger, o si no hay items cargados, no hacer nada.
        if not ctx.triggered or not items:
            raise PreventUpdate
        
        # 1. Recolectar todos los índices seleccionados
        selected_indices = set()
        for values in list_of_checkbox_values:
            # Los valores de un checklist siempre son listas. Si está marcado, contiene el índice [idx].
            if values:
                selected_indices.add(values[0])
        
        selected_indices_list = sorted(list(selected_indices))
        
        # 2. Crear el panel de resumen ("Combined Genes for Enrichment")
        if not selected_indices_list:
            # Retorna la lista vacía al Store y un mensaje al panel
            return selected_indices_list, html.Div("No items selected. Select items above to view the combined gene list.", className="text-muted p-3")

        # Lógica para contar genes combinados (similar a la de los callbacks de ejecución)
        combined_genes = set()
        for idx in selected_indices_list:
            if idx < len(items):
                item = items[idx]
                item_type = item.get('type', '')
                
                # Nota: Aquí se asume que el campo 'selected_genes' o 'genes' es correcto
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
        
        # 3. Renderizar el panel de resumen
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
    
    # 2.5. Callback para limpiar la selección de tarjetas (NUEVO)
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data', allow_duplicate=True),
         Output('enrichment-selection-panel', 'children', allow_duplicate=True)],
        Input('clear-enrichment-selection-btn', 'n_clicks'), # ID del nuevo botón
        prevent_initial_call=True
    )
    def clear_enrichment_selection(n_clicks):
        if n_clicks and n_clicks > 0:
            # Limpia el store de índices seleccionados y el panel de resumen
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
  

   # logic/callbacks/enrichment_analysis.py (Función run_gprofiler_analysis)

    # 4. Callback para ejecutar el análisis de g:Profiler (DEFINICIÓN ORIGINAL DE OUTPUT)
    @app.callback(
        # 🔑 CAMBIO CLAVE: DEFINICIÓN ORIGINAL (SIN allow_duplicate=True) 🔑
        Output('gprofiler-results-store', 'data'), 
        Input('run-gprofiler-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('gprofiler-organism-dropdown', 'value')],
        prevent_initial_call=True
    )
    def run_gprofiler_analysis(n_clicks, selected_indices, items, organism):
        """Executes g:Profiler enrichment analysis and stores results."""
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
            return {'results': [], 'gene_list': [], 'organism': organism}

        # 2. Ejecutar servicio de g:Profiler
        results = GProfilerService.get_enrichment(gene_list, organism)

        if results is None:
            return None 
        
        if not results:
             return {'results': [], 'gene_list': gene_list, 'organism': organism}


        # 3. Procesar resultados de g:Profiler
        enrichment_data_list = []
        for term in results:
            
            source_order_value = str(term.get('source_order', 'N/A'))
            
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
                'significant': term.get('significant', False)
            })

        # CAMBIO: Retorna un diccionario con los resultados, la lista de genes y el organismo
        return {
            'results': enrichment_data_list, 
            'gene_list': gene_list, 
            'organism': organism
        }

    # logic/callbacks/enrichment_analysis.py (Callback display_gprofiler_results CORREGIDO - ELIMINADO threshold_type)

    # 4.5. Callback para mostrar los resultados de g:Profiler (CORREGIDO - ELIMINADO threshold_type)
    @app.callback(
        [Output('gprofiler-results-content', 'children', allow_duplicate=True),
         Output('clear-gprofiler-results-btn', 'disabled', allow_duplicate=True),
         Output('gprofiler-manhattan-plot', 'figure', allow_duplicate=True)], 
        [Input('gprofiler-results-store', 'data'),
         Input('gprofiler-threshold-input', 'value')], # 🔑 CAMBIO CLAVE: Eliminado threshold_type 🔑
        [State('main-tabs', 'active_tab'),
         State('enrichment-service-tabs', 'active_tab')], 
        prevent_initial_call=True
    )
    def display_gprofiler_results(stored_data, threshold_value, main_active_tab, service_active_tab):
        
        # 🔑 PREVENCIÓN DE EJECUCIÓN 🔑
        if main_active_tab != 'enrichment-tab':
            raise PreventUpdate
        
        # Mapeo de códigos de organismo de g:Profiler a nombres comunes
        organism_map = {
            'hsapiens': 'Homo sapiens', 'mmusculus': 'Mus musculus', 'rnorvegicus': 'Rattus norvegicus',
            'drerio': 'Danio rerio', 'dmelanogaster': 'Drosophila melanogaster', 'celegans': 'Caenorhabditis elegans',
        }

        # 2. Inicialización y Desempaquetado
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

        
        # 3. Lógica de Filtrado Gold Standard (Ahora unificado)
        df = pd.DataFrame(enrichment_data_list)
        
        # 🔑 VALIDACIÓN SÓLIDA PARA OBTENER EL VALOR REAL DE FILTRO 🔑
        
        # Intentar convertir a float
        try:
            val_threshold = float(threshold_value)
        except (TypeError, ValueError):
            val_threshold = 0.05
        
        # Validación de rango y asignación para filtrado de tabla
        if not (0 < val_threshold <= 1.0):
            val_threshold = 0.05
        
        
        filtered_df = df.copy()

        # Filtrado Unificado (siempre sobre P-Value corregido)
        filtered_df = filtered_df[filtered_df['p_value'] < val_threshold]
        filter_message = f"Filtered results (P-Value corrected < {val_threshold})"
        
        
        # 4. Generación del Manhattan Plot
        df_plot = df[df['significant'] == True].copy() 
        
        # 🔑 CAMBIO CLAVE: Llamada a la función sin el parámetro threshold_type 🔑
        manhattan_fig = create_gprofiler_manhattan_plot(df_plot, threshold_value)
        
        
        # 5. Manejo de No Resultados Post-Filtro
        if filtered_df.empty:
            input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
            simplified_no_results_message = f"No **significant** pathways found after applying the Gold Standard filter ({val_threshold}).\n\n{input_message}"
            
            return html.Div(
                [
                    dbc.Alert([
                        html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")
                    ], color="info", className="mt-3")
                ]
            ), False, manhattan_fig

        
        # 6. Lógica de renderizado para RESULTADOS EXISTENTES (Tabla)
        
        display_df = filtered_df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False])
        display_df = display_df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'source_order_display']].copy()
        
        # Construcción del Mensaje Resumen
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_validated_name}**"
        pathways_message = f"Displaying **{len(display_df)}** terms. {filter_message}"
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        # ... (Configuración de columnas y tabla se mantienen igual) ...

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
        
        # Create results display
        results_content = [
            html.H4("g:Profiler Enrichment Results", className="mb-3"),
            
            # Mostrar el mensaje resumen con formato Markdown (incluye separación)
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

        return html.Div(results_content), False, manhattan_fig
        
    # 4.6. Callback para limpiar los resultados de g:Profiler (Mantenido)
    @app.callback(
        [Output('gprofiler-results-store', 'data', allow_duplicate=True),
         # SALIDA DUPLICADA: MANTENER allow_duplicate=True
         Output('gprofiler-manhattan-plot', 'figure', allow_duplicate=True)], 
        Input('clear-gprofiler-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_gprofiler_results(n_clicks):
        if n_clicks and n_clicks > 0:
            # CAMBIO: Retorna un diccionario vacío en el formato del Store y una figura vacía
            return {'results': [], 'gene_list': [], 'organism': 'hsapiens'}, go.Figure()
        raise PreventUpdate

    # 5. Callback para ejecutar el análisis de Reactome (CORREGIDO)
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

        # --- LOG DE DEBUGGING DE DASH INPUT ---
        logger.info(f"DASH INPUT DEBUG: Value read from dropdown 'reactome-organism-input' is: {organism_name}")
        
        # 2. Ejecutar servicio de Reactome
        service_response = ReactomeService.get_enrichment(gene_list, organism_name)

        if service_response is None:
            # Si hay error en API, devuelve None.
            return None
        
        # ACTUALIZACIÓN: DEVOLVER EL service_response COMPLETO
        service_response['gene_list'] = gene_list
        
        return service_response

    # 5.5. Callback para mostrar los resultados de Reactome (CORREGIDO: MANEJO DE NameError EN LA TABLA)
    @app.callback(
        [Output('reactome-results-content', 'children'),
         Output('clear-reactome-results-btn', 'disabled'),
         Output('reactome-diagram-output', 'children', allow_duplicate=True),
         Output('reactome-fireworks-output', 'children', allow_duplicate=True)], 
        Input('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def display_reactome_results(stored_data):
        
        # 1. Definir Placeholders
        placeholder_diagram = html.Div(
            dbc.Alert("Select a pathway from the table below to visualize the gene overlay.", color="secondary"), 
            className="p-3"
        )
        placeholder_fireworks = html.Div(
            dbc.Alert("Run analysis to view the genome-wide enrichment distribution.", color="info"), 
            className="p-3"
        )
        
        if stored_data is None or not isinstance(stored_data, dict):
            # No hay datos para mostrar
            raise PreventUpdate
        
        # Desempaquetar los datos del Store
        enrichment_data_list = stored_data.get('results', [])
        analysis_token = stored_data.get('token', 'N/A')
        organism_used_api = stored_data.get('organism_used_api', 'N/A')
        organism_selected = stored_data.get('organism_selected', 'N/A')
        gene_list = stored_data.get('gene_list', [])
        genes_analyzed = len(gene_list)
            
        
        # 2. Generación del IFRAME de Fireworks
        fireworks_content = placeholder_fireworks
        if analysis_token and analysis_token != 'N/A' and organism_used_api and len(enrichment_data_list) > 0:
            organism_encoded = organism_used_api.replace(' ', '%20')
            fireworks_url = (
                f"https://reactome.org/PathwayBrowser/?species={organism_encoded}"
                f"#DTAB=AN&ANALYSIS={analysis_token}"
            )
            
            # LOG CRÍTICO
            logger.info(f"FIREWORKS URL DEBUG: Final URL being sent to iFrame: {fireworks_url}")

            fireworks_content = html.Iframe(
                src=fireworks_url,
                style={"width": "100%", "height": "500px", "border": "none"},
                title=f"Reactome Pathway Browser/Fireworks visualization for {organism_used_api}"
            )

        
        # 3. Construcción del Mensaje Resumen
        input_message = f"**Sent (Input)::** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_used_api}** | Analysis Token: **{analysis_token}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant Reactome pathways."
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        # 4. Manejo de NO RESULTADOS (Inicialización del DataFrame vacío)
        if not enrichment_data_list:
            simplified_no_results_message = f"No significant pathways found in Reactome.\n\n{input_message}"
            results_content = html.Div(
                [dbc.Alert([html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")], color="info", className="mt-3")]
            )
            
            # 🔑 INICIALIZACIÓN DE DATAFRAMES VACÍOS para evitar NameError en la tabla 🔑
            df = pd.DataFrame()
            display_df = pd.DataFrame() 
            
            # Retorno inmediato para esta ruta
            return results_content, False, placeholder_diagram, fireworks_content


        # 5. Lógica de renderizado para RESULTADOS EXITOSOS (Tabla)
        # 🔑 CREACIÓN DE DATAFRAMES 🔑
        df = pd.DataFrame(enrichment_data_list)
        df = df.sort_values(by=['fdr_value', 'entities_found'], ascending=[True, False])
        display_df = df[['term_name', 'description', 'fdr_value', 'p_value', 'entities_found', 'entities_total']].copy()
        
        # 6. ASIGNACIÓN FINAL DE results_content (Para la ruta exitosa)
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

        # 7. Construcción de la tabla
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

        # 8. Retornar los 4 valores
        return html.Div(results_content), False, placeholder_diagram, fireworks_content



    # 6. 🚀 CALLBACK DE VISUALIZACIÓN DEL DIAGRAMA COLOREADO (NUEVO)
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
        if not stored_results or stored_results.get('token') in [None, 'N/A'] or stored_results.get('token').startswith('REF_'):
            return html.Div(dbc.Alert("Analysis Token not available or invalid.", color="warning"), className="p-3")

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
            file_format="png" # PNG para la mayoría de los diagramas, SVG para alta resolución
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
        
        
    # 6.5. Callback para limpiar los resultados de Reactome (Mantenido)
    @app.callback(
        # SALIDA DUPLICADA: MANTENER allow_duplicate=True
        Output('reactome-results-store', 'data', allow_duplicate=True),
        Input('clear-reactome-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_reactome_results(n_clicks):
        if n_clicks and n_clicks > 0:
            # Retorna un diccionario vacío en el formato del Store
            return {'results': [], 'gene_list': [], 'organism': 'Homo sapiens'}
        raise PreventUpdate
        
    # 7. 🔄 CALLBACK PARA AJUSTE DINÁMICO DE ANCHOS (Toggle Columns)
    @app.callback(
        # Output: Actualizar el estilo de la cabecera y el estilo de las celdas
        [Output('enrichment-results-table-gprofiler', 'style_header_conditional', allow_duplicate=True),
        Output('enrichment-results-table-gprofiler', 'style_data_conditional', allow_duplicate=True)],
        # Input: Escuchar la propiedad 'columns' que cambia cuando el usuario hace toggle
        Input('enrichment-results-table-gprofiler', 'columns'),
        # State: El estilo condicional que ya definimos (para no perderlo)
        State('enrichment-results-table-gprofiler', 'style_data_conditional'),
        prevent_initial_call=True
    )
    def adjust_gprofiler_column_widths_dynamically(current_columns, base_style_data_conditional):
        """
        Redistribuye el ancho de las columnas cuando el usuario oculta o muestra columnas.
        """
        if current_columns is None:
            raise PreventUpdate

        style_header_conditional = [] 
        style_data_conditional = base_style_data_conditional 
        
        return style_header_conditional, style_data_conditional