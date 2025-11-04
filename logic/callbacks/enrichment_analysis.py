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
  

   # logic/callbacks/enrichment_analysis.py (Función run_gprofiler_analysis CORREGIDA con source_order)

    # 4. Callback para ejecutar el análisis de g:Profiler (CORREGIDO: Extracción de source_order)
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
            return {'results': [], 'gene_list': [], 'organism': organism}

        # 2. Ejecutar servicio de g:Profiler
        results = GProfilerService.get_enrichment(gene_list, organism)

        if results is None:
            return None 
        
        if not results:
             return {'results': [], 'gene_list': gene_list, 'organism': organism}


        # 3. Procesar resultados de g:Profiler (REEMPLAZO DE COLUMNA 'INTERSECTIONS' POR 'source_order')
        enrichment_data_list = []
        for term in results:
            
            # 🔑 OBTENEMOS EL VALOR FUNCIONAL DE ORDEN (source_order) 🔑
            # (Lo convertimos a string para la tabla)
            source_order_value = str(term.get('source_order', 'N/A'))
            
            # NOTA: Eliminamos la extracción de 'intersections' ya que era la fuente del error de datos.
            
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
                # 🔑 AÑADIMOS LA CLAVE DE SALIDA QUE REEMPLAZA 'intersections' 🔑
                'source_order_display': source_order_value, 
                'significant': term.get('significant', False)
            })

        # CAMBIO: Retorna un diccionario con los resultados, la lista de genes y el organismo
        return {
            'results': enrichment_data_list, 
            'gene_list': gene_list, 
            'organism': organism
        }

    # logic/callbacks/enrichment_analysis.py (Fragmento de la Función display_gprofiler_results)

    # 4.5. Callback para mostrar los resultados de g:Profiler (CORREGIDO: Layout y NameError)
    @app.callback(
        [Output('gprofiler-results-content', 'children'),
         Output('clear-gprofiler-results-btn', 'disabled')], 
        Input('gprofiler-results-store', 'data')
    )
    def display_gprofiler_results(stored_data):
        
        # Mapeo de códigos de organismo de g:Profiler a nombres comunes
        organism_map = {
            'hsapiens': 'Homo sapiens', 'mmusculus': 'Mus musculus', 'rnorvegicus': 'Rattus norvegicus',
            'drerio': 'Danio rerio', 'dmelanogaster': 'Drosophila melanogaster', 'celegans': 'Caenorhabditis elegans',
        }

        # 🔑 CORRECCIÓN CLAVE: Inicialización de variables para evitar UnboundLocalError 🔑
        enrichment_data_list = []
        gene_list = []
        organism_code = 'N/A'
        organism_selected_name = 'N/A'
        organism_validated_name = 'N/A'
        
        # Manejo del estado de error grave o conexión fallida
        if stored_data is None:
            return dbc.Alert("Error connecting to g:Profiler API or receiving response.", color="danger"), True

        # Desempaquetar los datos del Store
        if isinstance(stored_data, dict):
            enrichment_data_list = stored_data.get('results', [])
            gene_list = stored_data.get('gene_list', [])
            organism_code = stored_data.get('organism', 'hsapiens')
            
            organism_selected_name = organism_map.get(organism_code, organism_code)
            organism_validated_name = organism_map.get(organism_code, organism_code)
        
        
        genes_analyzed = len(gene_list)

        if not enrichment_data_list and not gene_list:
            return html.Div("Click 'Run g:Profiler Analysis' to display results.", className="text-muted text-center p-4"), True

        
        # Construcción del Mensaje Resumen
        input_message = f"**Sent (Input):** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected_name}**"
        output_message = f"**Analized (Output):** Validated Organism: **{organism_validated_name}**"
        pathways_message = f"Found **{len(enrichment_data_list)}** significant terms."
        summary_message_md = f"{pathways_message}\n\n{input_message}\n\n{output_message}"
        
        # Manejo de No Resultados
        if not enrichment_data_list:
            simplified_no_results_message = f"No significant pathways found in g:Profiler.\n\n{input_message}"
            
            return html.Div(
                [
                    dbc.Alert([
                        html.P(dcc.Markdown(simplified_no_results_message, dangerously_allow_html=True), className="mb-0")
                    ], color="info", className="mt-3")
                ]
            ), False

        
        # Lógica de renderizado para RESULTADOS EXISTENTES
        df = pd.DataFrame(enrichment_data_list)
        
        if 'significant' in df.columns:
            df = df[df['significant'] == True]
        
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
        
        # 🔑 CAMBIO CLAVE: Definición del DataFrame de visualización 🔑
        # Eliminamos 'intersections' y usamos 'source_order_display'
        display_df = df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'source_order_display']].copy()
        
        # 🔑 CORRECCIÓN #1: Ocultar la columna 'source_order_display' por defecto.
        hidden_cols = ['source_order_display'] 

        # Configuración de columnas (CORREGIDA)
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
            # 🔑 NUEVA COLUMNA DE ORDENAMIENTO (source_order_display) 🔑
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
                
                # AJUSTES CLAVE DE ANCHO PARA PRIORIZAR DESCRIPCIÓN Y NOMBRE
                style_cell_conditional=[
                    {'if': {'column_id': 'term_name'}, 'width': '15%', 'minWidth': '100px', 'textAlign': 'left'}, 
                    {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px', 'maxWidth': '350px', 'textAlign': 'left'},
                    # La columna Source Order ya está oculta, pero mantenemos su ancho por si se muestra
                    {'if': {'column_id': 'source_order_display'}, 'width': '10%', 'minWidth': '60px', 'maxWidth': '80px', 'textAlign': 'center'}, 
                    {'if': {'column_id': 'p_value'}, 'width': '8%', 'minWidth': '70px', 'maxWidth': '80px', 'textAlign': 'center'},
                    {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'term_size'}, 'width': '5%', 'minWidth': '45px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'precision'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'recall'}, 'width': '7%', 'minWidth': '50px', 'maxWidth': '65px', 'textAlign': 'center'},
                    {'if': {'column_id': 'source'}, 'width': '7%', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
                ],
                
                style_cell={'padding': '8px', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'normal'},
                # 🔑 CORRECCIÓN #2: Modificación de style_header para permitir el apilamiento de texto/iconos
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'whiteSpace': 'normal', 
                    'height': 'auto',
                    'padding': '10px 8px' # Se reduce el padding superior/inferior
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                # ❌ ELIMINAMOS TOOLTIP DE INTERSECTIONS
                tooltip_duration=None,
            )
        ]

        return html.Div(results_content), False
    
# ... el resto del código del archivo enrichment_analysis.py se mantiene...
    

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

   # 5. Callback para ejecutar el análisis de Reactome (AÑADIDO LOG DE INPUT)
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
            # ... (Lógica de recolección de genes) ...
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

  

    # logic/callbacks/enrichment_analysis.py (Función display_reactome_results CORREGIDA)

# ... (El código anterior se mantiene igual hasta aquí) ...

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
            raise PreventUpdate
        
        # Desempaquetar los datos del Store
        enrichment_data_list = stored_data.get('results', [])
        analysis_token = stored_data.get('token', 'N/A')
        organism_used_api = stored_data.get('organism_used_api', 'N/A')
        organism_selected = stored_data.get('organism_selected', 'N/A')
        gene_list = stored_data.get('gene_list', [])
        genes_analyzed = len(gene_list)
            
        
        # 2. Generación del IFRAME de Fireworks
        # ... (código de generación de fireworks_content y URL se mantiene) ...
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
        input_message = f"**Sent (Input):** Analized Genes: **{genes_analyzed}** | Selected Organism: **{organism_selected}**"
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
        # ... (Código de configuración de columnas display_columns se mantiene) ...
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
            
            # 🔑 ESTA LÍNEA ES DONDE OCURRÍA EL ERROR 🔑
            dash_table.DataTable(
                id='enrichment-results-table-reactome', 
                data=display_df.to_dict('records'), # AHORA display_df está definido en todos los caminos
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
    # 7. 🔄 CALLBACK PARA AJUSTE DINÁMICO DE ANCHOS (Toggle Columns)
    @app.callback(
        # Output: Actualizar el estilo de la cabecera y el estilo de las celdas
        [Output('enrichment-results-table-gprofiler', 'style_header_conditional'),
        Output('enrichment-results-table-gprofiler', 'style_data_conditional')],
        # Input: Escuchar la propiedad 'columns' que cambia cuando el usuario hace toggle
        Input('enrichment-results-table-gprofiler', 'columns'),
        # State: El estilo condicional que ya definimos (para no perderlo)
        State('enrichment-results-table-gprofiler', 'style_data_conditional')
    )
    def adjust_gprofiler_column_widths_dynamically(current_columns, base_style_data_conditional):
        """
        Redistribuye el ancho de las columnas cuando el usuario oculta o muestra columnas
        para que Intersections y Description tengan suficiente espacio.
        """
        if current_columns is None:
            raise PreventUpdate

        # Verificar si 'intersections' está visible
        is_intersections_visible = any(col['id'] == 'intersections' and not col.get('hidden', False) for col in current_columns)

        if is_intersections_visible:
            # 🔑 MODO ANCHO (Prioridad a Intersections y Description) 🔑
            
            # Estilo para la cabecera (Header Style)
            style_header_conditional = [
                {'if': {'column_id': 'intersections'}, 'minWidth': '150px', 'width': '20%', 'maxWidth': '300px'},
                {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px'},
                # Reducir el resto de columnas numéricas para liberar espacio
                {'if': {'column_id': 'term_size'}, 'width': '5%', 'minWidth': '40px'},
                {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '40px'},
                {'if': {'column_id': 'source'}, 'width': '5%', 'minWidth': '40px'},
            ]
            
            # Estilo para los datos (Data Style) - Mismos anchos
            style_data_conditional = [
                {'if': {'column_id': 'intersections'}, 'minWidth': '150px', 'width': '20%', 'maxWidth': '300px'},
                {'if': {'column_id': 'description'}, 'width': '35%', 'minWidth': '150px'},
                {'if': {'column_id': 'term_size'}, 'width': '5%', 'minWidth': '40px'},
                {'if': {'column_id': 'intersection_size'}, 'width': '5%', 'minWidth': '40px'},
                {'if': {'column_id': 'source'}, 'width': '5%', 'minWidth': '40px'},
            ]

        else:
            # 🛡️ MODO POR DEFECTO (Las columnas de texto tienen un ancho razonable) 🛡️
            # Aquí podemos usar los anchos definidos en el estilo original de style_cell_conditional
            
            style_header_conditional = [] # No necesitamos un estilo header condicional complejo en modo normal
            
            # Usamos el estilo condicional que ya definimos en style_cell_conditional para el modo por defecto
            # (Se asume que style_data_conditional del DataTable está bien configurado con style_cell_conditional)
            style_data_conditional = base_style_data_conditional # Usar el estilo base del DataTable

        
        # Nota: DataTable solo acepta style_data_conditional, no style_header_conditional en la práctica para anchos.
        # Usaremos style_data_conditional para anchos y style_header_conditional para el fondo.
        
        # Dado que los anchos se definen en style_cell_conditional (que ya está en tu layout), 
        # simplemente actualizamos esa propiedad aquí.

        # En Dash, los anchos se deben aplicar en style_data_conditional o style_cell_conditional.
        # El style_header_conditional es principalmente para colores y fuentes. 
        
        # Para ser puristas, devolvemos el cambio en las propiedades que controlan el ancho del contenido:
        return style_header_conditional, style_data_conditional