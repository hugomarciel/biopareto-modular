# logic/callbacks/export_callbacks.py

import dash
from dash import Output, Input, State, dcc, html, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import json
import pandas as pd
from datetime import datetime
from services.report_generator import (
    generate_pdf_report,
    generate_txt_report,
    export_pareto_data,
    export_genes_list
)


def register_export_callbacks(app):
    """
    Register all callbacks for the Export tab.
    """

    # Selector visual de ítems (single-select)
    @app.callback(
        Output('export-items-visual-selector', 'children'),
        [Input('interest-panel-store', 'data'),
         Input('export-selected-indices-store', 'data')]
    )
    def render_export_selector(items, selected_indices_list):
        if not items:
            return dbc.Alert([
                html.I(className="bi bi-info-circle me-2"),
                "No items available. Add items to your Interest Panel first."
            ], color="light", className="d-flex align-items-center small mb-0")

        if selected_indices_list is None:
            selected_indices_list = []

        type_map = {
            'solution': ("primary", "🔵", "Solution"),
            'solution_set': ("info", "📦", "Set"),
            'gene_set': ("success", "🧬", "Gene Group"),
            'individual_gene': ("warning", "🔬", "Gene"),
            'combined_gene_group': ("success", "🎯", "Combined")
        }

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            badge_color, icon, badge_text = type_map.get(item_type, ("secondary", "❓", "Item"))
            item_name = item.get('name', 'Unknown')
            item_comment = item.get('comment', '')
            item_origin = item.get('tool_origin', 'Manual Selection')
            data = item.get('data', {})

            stats_left = ""
            stats_right = ""
            if item_type == 'solution':
                genes = data.get('selected_genes', [])
                stats_left = f"Genes: {len(genes)}"
                stats_right = f"Src: {data.get('front_name', '?')}"
            elif item_type == 'solution_set':
                n_genes = data.get('unique_genes_count', 0)
                if n_genes == 0 and 'solutions' in data:
                    unique_g = set()
                    for s in data['solutions']:
                        unique_g.update(s.get('selected_genes', []))
                    n_genes = len(unique_g)
                stats_left = f"Genes: {n_genes}"
                stats_right = f"Sols: {len(data.get('solutions', []))}"
            elif item_type == 'gene_set':
                stats_left = f"Genes: {len(data.get('genes', []))}"
                freq = data.get('frequency')
                stats_right = f"Freq: {freq}%" if freq else "Table"
            elif item_type == 'individual_gene':
                stats_left = f"ID: {data.get('gene')}"
                stats_right = f"Src: {data.get('source')}"
            elif item_type == 'combined_gene_group':
                stats_left = f"Genes: {data.get('gene_count', 0)}"
                stats_right = f"Srcs: {len(data.get('source_items', []))}"

            is_selected = idx in selected_indices_list
            card_style = {'transition': 'all 0.2s ease-in-out', 'border': '2px solid #0d6efd', 'backgroundColor': '#f0f8ff', 'transform': 'scale(1.02)', 'cursor': 'pointer'} if is_selected else \
                         {'transition': 'all 0.2s ease-in-out', 'border': '1px solid rgba(0,0,0,0.125)', 'backgroundColor': 'white', 'transform': 'scale(1)', 'cursor': 'pointer'}
            card_class = "h-100 shadow" if is_selected else "h-100 shadow-sm hover-shadow"

            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=[idx] if is_selected else [],
                                id={'type': 'export-card-checkbox', 'index': idx},
                                switch=True,
                                style={'transform': 'scale(1.3)'}
                            )
                        ], style={'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': '10'}),

                        html.Div([
                            html.Div([
                                html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                                dbc.Badge(badge_text, color=badge_color, style={'fontSize': '0.75rem'}),
                            ], className="d-flex align-items-center mb-2"),
                            
                            html.H6(item_name, className="fw-bold mb-2 text-truncate", title=item_name, style={'maxWidth': '90%'}),
                            html.Hr(className="my-2"),
                            html.Div([
                                html.Span(stats_left, className="fw-bold text-primary"),
                                html.Span(" | ", className="text-muted mx-1"),
                                html.Span(stats_right, className="text-muted text-truncate")
                            ], className="small mb-2"),
                            html.P(item_comment, className="text-muted small fst-italic mb-0 text-truncate", title=item_comment) if item_comment else None,
                            html.Div([html.Small(f"Via: {item_origin}", className="text-muted", style={'fontSize': '0.65rem'})], className="mt-2 pt-1 border-top")
                        ], style={'paddingRight': '25px'})
                    ], className="p-3")
                ], id={'type': 'export-card-wrapper', 'index': idx}, className=card_class, style=card_style)
            ], width=12, md=6, lg=4, xl=3, className="mb-3")

            cards.append(card)

        return dbc.Row(cards, className="g-3")

    # Store para selección única (mantiene solo el último seleccionado)
    @app.callback(
        Output('export-selected-indices-store', 'data'),
        Input({'type': 'export-card-checkbox', 'index': ALL}, 'value'),
        prevent_initial_call=True
    )
    def enforce_single_selection(checkbox_values):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            trigger_id = json.loads(trigger_id_str)
        except Exception:
            raise PreventUpdate

        idx = trigger_id.get('index')
        if idx is None:
            raise PreventUpdate

        # Intentamos leer el valor disparado; si no viene, usamos la lista por índice.
        triggered_value = ctx.triggered[0].get('value', None)
        if triggered_value is None and 0 <= idx < len(checkbox_values):
            triggered_value = checkbox_values[idx]

        # Si se activó el switch, seleccionamos solo ese índice; si se apagó, limpiamos.
        if triggered_value:
            return [idx]
        return []

    # 1. Callback para generar PDF Report
    @app.callback(
        Output("pdf-report-download", "data"),
        Input("generate-pdf-report", "n_clicks"),
        [State('data-store', 'data'),
         State('enrichment-data-store', 'data')],
        prevent_initial_call=True
    )
    def download_pdf_report(n_clicks, data_store, enrichment_data):
        if not n_clicks or not data_store or not data_store.get('fronts'):
            raise PreventUpdate

        pdf_buffer = generate_pdf_report(data_store, enrichment_data)
        if pdf_buffer:
            return dcc.send_bytes(pdf_buffer.getvalue(), f"BioPareto_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        raise PreventUpdate

    # 2. Callback para generar TXT Report
    @app.callback(
        Output("txt-report-download", "data"),
        Input("generate-txt-report", "n_clicks"),
        [State('data-store', 'data'),
         State('enrichment-data-store', 'data')],
        prevent_initial_call=True
    )
    def download_txt_report(n_clicks, data_store, enrichment_data):
        if not n_clicks or not data_store or not data_store.get('fronts'):
            raise PreventUpdate

        txt_content = generate_txt_report(data_store, enrichment_data)
        if txt_content:
            return dcc.send_string(txt_content, f"BioPareto_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        raise PreventUpdate

    # 3. Exportar Pareto Data (CSV)
    @app.callback(
        Output("download-pareto-csv", "data"),
        Input("btn-export-pareto-csv", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_pareto_csv(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
        csv_data = export_pareto_data(data_store, 'csv')
        if csv_data:
            return dcc.send_string(csv_data, f"pareto_solutions_{datetime.now().strftime('%Y%m%d')}.csv")
        raise PreventUpdate

    # 4. Exportar Pareto Data (JSON)
    @app.callback(
        Output("download-pareto-json", "data"),
        Input("btn-export-pareto-json", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_pareto_json(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
        json_data = export_pareto_data(data_store, 'json')
        if json_data:
            return dcc.send_string(json_data, f"pareto_solutions_{datetime.now().strftime('%Y%m%d')}.json")
        raise PreventUpdate

    # 5. Exportar Lista de Genes (CSV)
    @app.callback(
        Output("download-genes-csv", "data"),
        Input("btn-export-genes-csv", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_genes_csv(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
        csv_data = export_genes_list(data_store, 'csv')
        if csv_data:
            return dcc.send_string(csv_data, f"unique_genes_{datetime.now().strftime('%Y%m%d')}.csv")
        raise PreventUpdate

    # 6. Exportar Lista de Genes (TXT)
    @app.callback(
        Output("download-genes-txt", "data"),
        Input("btn-export-genes-txt", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_genes_txt(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
        txt_data = export_genes_list(data_store, 'txt')
        if txt_data:
            return dcc.send_string(txt_data, f"unique_genes_{datetime.now().strftime('%Y%m%d')}.txt")
        raise PreventUpdate

    # 7. Resumen de la sesión
    @app.callback(
        Output('session-summary', 'children'),
        Input('data-store', 'data'),
        State('interest-panel-store', 'data')
    )
    def update_session_summary(data_store, interest_items):
        if not data_store:
            return dbc.Alert("No data loaded.", color="warning")

        fronts = data_store.get('fronts', [])
        all_solutions = [s for f in fronts for s in f.get('data', []) if f.get('visible', True)]
        unique_genes = set(g for sol in all_solutions for g in sol.get('selected_genes', []))

        return dbc.ListGroup([
            dbc.ListGroupItem(f"Loaded Fronts: {len(fronts)}"),
            dbc.ListGroupItem(f"Total Solutions: {len(all_solutions)}"),
            dbc.ListGroupItem(f"Unique Genes: {len(unique_genes)}"),
            dbc.ListGroupItem(f"Items in Interest Panel: {len(interest_items) if interest_items else 0}"),
        ])
