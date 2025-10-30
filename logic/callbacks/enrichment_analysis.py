# logic/callbacks/enrichment_analysis.py

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
from services.gprofiler_service import GProfilerService 


def register_enrichment_callbacks(app): 

    # 1. Callback de Actualización de IDs y Trigger
    # logic/callbacks/enrichment_analysis.py (Fragmento de Código)

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

            # 🔑 Lógica de creación de tarjeta (REPLICADA DE GENE GROUPS ANALYSIS) 🔑
            
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
                                # 🔑 CORRECCIÓN ID: Usamos 'enrichment-card-checkbox' como ID de tipo
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


    # 2. Callback para manejar la selección de los checkboxes y actualizar el panel de resumen
    # ... (Resto de callbacks se mantiene) ...
   # logic/callbacks/enrichment_analysis.py (FRAGMENTO)

# ... (cerca de la línea 130)

    # 2. Callback para manejar la selección de los checkboxes y actualizar el panel de resumen
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data'),
         Output('enrichment-selection-panel', 'children')],
        Input({'type': 'enrichment-card-checkbox', 'index': ALL}, 'value'), 
        State('interest-panel-store', 'data')
    )
    def update_enrichment_selection(checkbox_values, items):
        """Processes selection checkboxes and updates the summary panel."""
        
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        selected_indices = []
        
        # Iteramos sobre los inputs disparados para obtener el ID real (índice)
        for input_info in ctx.inputs_list[0]:
            # El valor del input es una lista [índice] si está marcado, o [] si no.
            if input_info['value'] and len(input_info['value']) > 0:
                 # El valor del checkbox es el índice real del ítem en el interest-panel-store
                 selected_indices.append(input_info['value'][0]) 
        
        if not selected_indices:
            return [], dbc.Alert("No items selected for analysis.", color="warning")

        # Lógica de agregación de genes (se mantiene igual, usando selected_indices)
        combined_genes = set()
        selected_names = []
        
        for idx in selected_indices:
            if idx >= len(items):
                continue
            
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
            
            selected_names.append(item.get('name'))


        # Almacenar la lista de genes combinados para el análisis
        combined_genes_list = sorted(list(combined_genes))

        # Renderizar el panel de resumen de la selección
        summary_panel = dbc.Card([
            dbc.CardHeader("Combined Genes for Enrichment"),
            dbc.CardBody([
                html.P(f"Total Unique Genes: {len(combined_genes_list)}", className="mb-1"),
                html.P(f"Sources: {len(selected_indices)} item(s)"),
                html.Details([
                    html.Summary("View Sources"),
                    dbc.ListGroup([
                        dbc.ListGroupItem(name, className="small py-1") for name in selected_names
                    ], flush=True, className="mt-2")
                ])
            ])
        ])

        return selected_indices, summary_panel

# ... (El resto del archivo enrichment_analysis.py se mantiene igual)


    # 3. Callback para habilitar el botón de enriquecimiento
    @app.callback(
        Output('run-enrichment-btn', 'disabled'), 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices): # <- FUNCIÓN FINAL
        """Habilitar/deshabilitar botón de enriquecimiento si hay genes seleccionados."""
        if not selected_indices:
            return True
        return False


    # 4. Callback para ejecutar el análisis de enriquecimiento biológico
    @app.callback(
        [Output('enrichment-data-store', 'data'),
         Output('enrichment-results', 'children')], 
        Input('run-enrichment-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('organism-dropdown', 'value')], 
        prevent_initial_call=True
    )
    def run_enrichment_analysis(n_clicks, selected_indices, items, organism):
        """Executes g:Profiler enrichment analysis and stores results."""
        if not n_clicks or not selected_indices:
            raise PreventUpdate

        # 1. Recolectar lista final de genes
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
            return None, dbc.Alert("No genes found in the selected items to run enrichment.", color="warning")

        # 2. Ejecutar servicio de g:Profiler
        results = GProfilerService.get_enrichment(gene_list, organism)

        if results is None:
            return None, dbc.Alert("Error connecting to g:Profiler API or receiving response.", color="danger")
        
        if not results:
             return results, dbc.Alert(f"g:Profiler found no significant enrichment results for {len(gene_list)} genes in {organism}.", color="info")

        # 3. Procesar resultados de g:Profiler con los nombres de campo correctos
        enrichment_data_list = []
        for term in results:
            # Handle intersections properly - g:Profiler returns 'intersections' (plural)
            intersections = term.get('intersections', [])
            if isinstance(intersections, list):
                # Flatten the list of lists into a single list of strings
                flat_intersections = [str(item) for sublist in intersections for item in (sublist if isinstance(sublist, list) else [sublist])]
                intersections_str = ', '.join(flat_intersections)
            else:
                intersections_str = str(intersections)

            enrichment_data_list.append({
                'source': term.get('source', ''),
                'term_name': term.get('name', ''),  # g:Profiler uses 'name' not 'term_name'
                'description': term.get('description', ''),
                'p_value': term.get('p_value', 1.0),
                'term_size': term.get('term_size', 0),
                'query_size': term.get('query_size', 0),
                'intersection_size': term.get('intersection_size', 0),
                'precision': term.get('precision', 0.0),
                'recall': term.get('recall', 0.0),
                'intersections': intersections_str,  # g:Profiler uses 'intersections' (plural)
                'significant': term.get('significant', False)
            })

        # Convert to DataFrame
        df = pd.DataFrame(enrichment_data_list)
        
        # Filter for significant terms only
        if 'significant' in df.columns:
            df = df[df['significant'] == True]
        
        if df.empty:
            return enrichment_data_list, dbc.Alert(f"No significant enrichment results found for {len(gene_list)} genes.", color="info")
        
        # Sort by p-value and intersection size
        df = df.sort_values(by=['p_value', 'intersection_size'], ascending=[True, False])
        
        # Select and rename columns for display
        display_df = df[['source', 'term_name', 'description', 'p_value', 'intersection_size', 'term_size', 'precision', 'recall', 'intersections']].copy()
        # </CHANGE>
        
        # Configure columns for DataTable
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
            html.H4("Enrichment Analysis Results", className="mb-3"),
            html.P(f"Found {len(df)} significant terms for {len(gene_list)} unique genes.", className="text-muted"),
            
            dash_table.DataTable(
                id='enrichment-results-table',
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

        return enrichment_data_list, html.Div(results_content)
