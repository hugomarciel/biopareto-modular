# logic/callbacks/enrichment_analysis.py (CÓDIGO FINAL CON VISUALIZACIÓN DE DIAGRAMA)

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import logging

# Importamos AMBOS servicios
from services.gprofiler_service import GProfilerService 
from services.reactome_service import ReactomeService 

logger = logging.getLogger(__name__)

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
    
   # 4. Callback para ejecutar el análisis de g:Profiler (Mantenido)
    @app.callback(
        # CAMBIO: Ahora guarda en un Store específico para g:Profiler
        Output('gprofiler-results-store', 'data', allow_duplicate=True), 
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
            # CAMBIO: Retornar diccionario con lista de resultados vacía
            return {'results': [], 'gene_list': [], 'organism': organism}

        # 2. Ejecutar servicio de g:Profiler
        results = GProfilerService.get_enrichment(gene_list, organism)

        if results is None:
            # Si hay error en API, devuelve None. El display callback lo manejará.
            return None 
        
        if not results:
             # Si no hay resultados, devuelve lista vacía.
             # CAMBIO: Retornar diccionario con lista de resultados vacía
             return {'results': [], 'gene_list': gene_list, 'organism': organism}


        # 3. Procesar resultados de g:Profiler
        enrichment_data_list = []
        for term in results:
            intersections = term.get('intersections', [])
            if isinstance(intersections, list):
                # Lógica para aplanar la lista de intersecciones
                flat_intersections = []
                for sublist in intersections:
                    if isinstance(sublist, list):
                        flat_intersections.extend([str(item) for item in sublist])
                    else:
                        flat_intersections.append(str(sublist))
                intersections_str = ', '.join(flat_intersections)
            else:
                intersections_str = str(intersections)

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
                'intersections': intersections_str,  
                'significant': term.get('significant', False)
            })

        # CAMBIO: Retorna un diccionario con los resultados, la lista de genes y el organismo
        return {
            'results': enrichment_data_list, 
            'gene_list': gene_list, 
            'organism': organism
        }


    # 4.5. Callback para mostrar los resultados de g:Profiler (Mantenido)
    @app.callback(
        [Output('gprofiler-results-content', 'children'),
         Output('clear-gprofiler-results-btn', 'disabled')], 
        Input('gprofiler-results-store', 'data')
    )
    def display_gprofiler_results(stored_data):
        
        # Mapeo de códigos de organismo de g:Profiler a nombres comunes
        organism_map = {
            'hsapiens': 'Homo sapiens',
            'mmusculus': 'Mus musculus',
            'rnorvegicus': 'Rattus norvegicus',
            'drerio': 'Danio rerio',
            'dmelanogaster': 'Drosophila melanogaster',
            'celegans': 'Caenorhabditis elegans',
            # Añadir más si es necesario
        }

        # 🔑 CORRECCIÓN: Inicialización segura de variables clave 🔑
        enrichment_data_list = []
        gene_list = []
        organism_code = 'N/A'
        organism_selected_name = 'N/A'
        organism_validated_name = 'N/A'
        
        # Manejo del estado de error grave o conexión fallida
        if stored_data is None:
            return dbc.Alert("Error connecting to g:Profiler API or receiving response.", color="danger"), True

        # Desempaquetar los datos del Store (que ya no es None, sino un dict o lista)
        if isinstance(stored_data, dict):
            enrichment_data_list = stored_data.get('results', [])
            gene_list = stored_data.get('gene_list', [])
            organism_code = stored_data.get('organism', 'hsapiens')
            
            # Datos para el mensaje
            organism_selected_name = organism_map.get(organism_code, organism_code)
            organism_validated_name = organism_map.get(organism_code, organism_code)
        
        
        genes_analyzed = len(gene_list)

        # 🔑 MANEJO DEL ESTADO INICIAL (STORE VACÍO) 🔑
        if not enrichment_data_list and not gene_list:
            # Estado inicial (antes del primer análisis) o después de Clear.
            return html.Div("Click 'Run g:Profiler Analysis' to display results.", className="text-muted text-center p-4"), True

        
        # 🔑 CONSTRUCCIÓN DEL MENSAJE RESUMEN CON SEPARACIÓN (SIN TOKEN) 🔑
        
        # Mensaje de Input (Enviado)
        input_message = f"**Sent (Input):** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
        
        # Mensaje de Output (Recibido/Analizado)
        output_message = f"**Analized (Output):** Validated Organism: **{organism_validated_name}**"
        
        pathways_message = f"Found **{len(enrichment_data_list)}** significant terms."
        
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        # 🔑 MANEJO DE NO RESULTADOS Y MENSAJE INFORMATIVO SIMPLIFICADO 🔑
        if not enrichment_data_list:
            
            # Mensaje simplificado para no resultados
            simplified_no_results_message = f"No significant pathways found in g:Profiler.\n\n{input_message}"
            
            return html.Div(
                [
                    dbc.Alert([
                        html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")
                    ], color="info", className="mt-3")
                ]
            ), False # Habilita el botón de limpiar

        
        # Lógica de renderizado para RESULTADOS EXISTENTES
        df = pd.DataFrame(enrichment_data_list)
        
        # Filtramos por significancia (solo resultados significativos)
        if 'significant' in df.columns:
            df = df[df['significant'] == True]
        
        # Si el DataFrame queda vacío después del filtrado
        if df.empty:
            simplified_no_results_message = f"No **significant** pathways found in g:Profiler after filtering.\n\n{input_message}"
            
            return html.Div(
                [
                    dbc.Alert([
                        html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")
                    ], color="info", className="mt-3")
                ]
            ), False

        df = df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False])
        display_df = df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'intersections']].copy()
        
        # Configuración de columnas (se mantiene)
        display_columns = []
        for col in display_df.columns:
            if col == 'p_value':
                column_config = {
                    'name': 'P-Value', 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.2e'}
                }
            elif col == 'intersection_size':
                column_config = {
                    'name': 'Genes\nMatched', 'id': col, 'type': 'numeric'
                }
            elif col == 'term_size':
                column_config = {
                    'name': 'Term\nSize', 'id': col, 'type': 'numeric'
                }
            elif col == 'term_name':
                column_config = {
                    'name': 'Term Name', 'id': col, 'type': 'text'
                }
            elif col in ['precision', 'recall']:
                column_config = {
                    'name': col.capitalize(), 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.3f'}
                }
            else:
                column_config = {'name': col.capitalize(), 'id': col, 'type': 'text'}
            
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
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=15,
                style_cell={
                    'textAlign': 'left',
                    'padding': '8px',
                    'maxWidth': '200px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                tooltip_data=[
                    {
                        'intersections': {'value': row['intersections'], 'type': 'text'},
                        'description': {'value': row['description'], 'type': 'text'}
                    } for row in display_df.to_dict('records')
                ],
                tooltip_duration=None,
            )
        ]

        return html.Div(results_content), False


    # 4.6. Callback para limpiar los resultados de g:Profiler (Mantenido)
    @app.callback(
        Output('gprofiler-results-store', 'data', allow_duplicate=True),
        Input('clear-gprofiler-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_gprofiler_results(n_clicks):
        if n_clicks and n_clicks > 0:
            # CAMBIO: Retorna un diccionario vacío en el formato del Store
            return {'results': [], 'gene_list': [], 'organism': 'hsapiens'}
        raise PreventUpdate

   # 5. Callback para ejecutar el análisis de Reactome (Mantenido)
    @app.callback(
        # CAMBIO: Ahora guarda en un Store específico para Reactome
        Output('reactome-results-store', 'data', allow_duplicate=True), 
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
        # El servicio ahora retorna un diccionario: {'results': [...], 'token': '...', 'organism_used': '...'}
        service_response = ReactomeService.get_enrichment(gene_list, organism_name)

        if service_response is None:
            # Si hay error en API, devuelve None.
            return None
        
        # ACTUALIZACIÓN: DEVOLVER EL service_response COMPLETO
        service_response['gene_list'] = gene_list
        
        return service_response

  



   # 5.5. Callback para mostrar los resultados de Reactome (CORREGIDO: ELIMINACIÓN DE 'SOURCE' Y AJUSTE DE ANCHOS)
    @app.callback(
        [Output('reactome-results-content', 'children'),
         Output('clear-reactome-results-btn', 'disabled'),
         # NUEVO: Resetear el contenedor del diagrama al mostrar nuevos resultados de la tabla
         Output('reactome-diagram-output', 'children', allow_duplicate=True)], 
        Input('reactome-results-store', 'data'),
        prevent_initial_call=True
    )
    def display_reactome_results(stored_data):
        
        # Resetear el contenedor del diagrama a un placeholder
        placeholder_diagram = html.Div(
            dbc.Alert("Select a pathway from the table below to visualize the gene overlay.", color="secondary"), 
            className="p-3"
        )
        
        if stored_data is None or not isinstance(stored_data, dict):
            # Estado inicial o error de conexión
            return html.Div("Click 'Run Reactome Analysis' to display results.", className="text-muted text-center p-4"), True, placeholder_diagram

        # Desempaquetar los datos del Store
        enrichment_data_list = stored_data.get('results', [])
        analysis_token = stored_data.get('token', 'N/A')
        organism_used_api = stored_data.get('organism_used_api', 'N/A')
        organism_selected = stored_data.get('organism_selected', 'N/A')
        gene_list = stored_data.get('gene_list', [])
        genes_analyzed = len(gene_list)
            
        
        # 🔑 CONSTRUCCIÓN DEL MENSAJE RESUMEN 🔑
        
        input_message = f"**Sent (Input):** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_used_api}** | Analysis Token: **{analysis_token}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant Reactome pathways."
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        # 🔑 MANEJO DE NO RESULTADOS 🔑
        if not enrichment_data_list:
            simplified_no_results_message = f"No significant pathways found in Reactome.\n\n{input_message}"
            return html.Div(
                [dbc.Alert([html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")], color="info", className="mt-3")]
            ), False, placeholder_diagram

        
        # Lógica de renderizado para RESULTADOS EXISTENTES
        df = pd.DataFrame(enrichment_data_list)
        df = df.sort_values(by=['fdr_value', 'entities_found'], ascending=[True, False])
        
        # 1. ❌ ELIMINAR 'source' de la lista de columnas ❌
        display_df = df[['term_name', 'description', 'fdr_value', 'p_value', 'entities_found', 'entities_total']].copy()
        
        # Lista de IDs de columnas a ocultar
        hidden_cols = ['description']
        
        # Configuración de columnas
        display_columns = []
        for col in display_df.columns:
            # 1. Ajuste para FDR
            if col == 'fdr_value':
                 column_config = {
                    'name': 'FDR\n(Corrected P-Value)', 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.2e'},
                    'hideable': True
                }
            # 2. Ajuste para P-Value
            elif col == 'p_value':
                column_config = {
                    'name': 'P-Value', 'id': col, 'type': 'numeric',
                    'format': {'specifier': '.2e'},
                    'hideable': True
                }
            # 3. Ajuste para Genes Matched
            elif col == 'entities_found':
                column_config = {
                    'name': 'Genes\nMatched', 'id': col, 'type': 'numeric',
                    'hideable': True
                }
            # 4. Ajuste para Pathway Size
            elif col == 'entities_total':
                column_config = {
                    'name': 'Pathway\nSize', 'id': col, 'type': 'numeric',
                    'hideable': True
                }
            # 5. Pathway Name
            elif col == 'term_name':
                column_config = {
                    'name': 'Pathway Name', 'id': col, 'type': 'text',
                    'hideable': True
                }
            # 6. ST_ID (Oculto)
            elif col == 'description': 
                 column_config = {
                    'name': 'ST_ID', 'id': col, 'type': 'text' 
                }
            else:
                column_config = {'name': col.capitalize(), 'id': col, 'type': 'text', 'hideable': True}
            
            # 2. ❌ ELIMINAR ASIGNACIÓN DE ANCHO (width, minWidth, maxWidth) DENTRO DE ESTE BUCLE ❌
            # Esto corrige el error 'Invalid component prop columns[0] key width supplied'
            
            display_columns.append(column_config)
        
        # Create results display
        results_content = [
            html.H4("Reactome Enrichment Results", className="mb-3"), 
            
            # Mostrar el mensaje resumen con formato Markdown (incluye Token)
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
                
                # 🔑 AJUSTES DE ESTILO PARA CONTROLAR EL DESBORDAMIENTO Y PRIORIZAR 'Pathway Name' 🔑
                style_table={'overflowX': 'auto', 'minWidth': '100%'}, 
                
                style_cell_conditional=[
                    # 🎯 PRIORIDAD: Dar el 50% del ancho a Pathway Name
                    {'if': {'column_id': 'term_name'}, 'width': '50%', 'minWidth': '150px', 'textAlign': 'left'},
                    # Reducir el ancho de las columnas numéricas
                    {'if': {'column_id': 'fdr_value'}, 'width': '15%', 'minWidth': '70px', 'maxWidth': '90px'},
                    {'if': {'column_id': 'p_value'}, 'width': '15%', 'minWidth': '70px', 'maxWidth': '90px'},
                    {'if': {'column_id': 'entities_found'}, 'width': '10%', 'minWidth': '50px', 'maxWidth': '70px'},
                    {'if': {'column_id': 'entities_total'}, 'width': '10%', 'minWidth': '50px', 'maxWidth': '70px'},
                ],
                style_cell={
                    'textAlign': 'center', # El texto por defecto va centrado
                    'padding': '8px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
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
                tooltip_data=[
                    {'description': {'value': row['description'], 'type': 'text'}} for row in display_df.to_dict('records')
                ],
                tooltip_duration=None,
            )
        ]

        # Retornar los resultados, habilitar limpieza, y resetear el diagrama
        return html.Div(results_content), False, placeholder_diagram









    # 6. 🚀 CALLBACK DE VISUALIZACIÓN DEL DIAGRAMA COLOREADO (NUEVO)
    @app.callback(
        Output('reactome-diagram-output', 'children'),
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
        Output('reactome-results-store', 'data', allow_duplicate=True),
        Input('clear-reactome-results-btn', 'n_clicks'), 
        prevent_initial_call=True
    )
    def clear_reactome_results(n_clicks):
        if n_clicks and n_clicks > 0:
            # Retorna un diccionario vacío en el formato del Store
            return {'results': [], 'gene_list': [], 'organism': 'Homo sapiens'}
        raise PreventUpdate