# logic/callbacks/export_callbacks.py

import dash
from dash import Output, Input, State, dcc, html, dash_table, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import json
from datetime import datetime
from services.report_generator import (
    generate_pdf_report,
    generate_txt_report,
    export_pareto_data,
    export_genes_list
)


def register_export_callbacks(app):
    """Register callbacks for Export tab."""

    # Selector visual (single-select)
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

        selected_indices_list = selected_indices_list or []

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
                genes = data.get('genes', [])
                stats_left = f"Genes: {len(genes)}"
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

    # Detalle del item seleccionado
    @app.callback(
        [Output('export-selected-item-details', 'children'),
         Output('export-attachments-preview', 'children'),
         Output('export-comment-editor', 'value')],
        Input('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=False
    )
    def render_selected_item_details(selected_indices, items):
        if not selected_indices or not items:
            placeholder = dbc.Alert([
                html.I(className="bi bi-hand-index me-2"),
                "Select an item above to see its details."
            ], color="light", className="d-flex align-items-center small mb-0")
            return placeholder, None, ""

        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate
        item = items[idx]
        item_type = item.get('type', 'Unknown')
        name = item.get('name', 'Unknown')
        comment = item.get('comment', '') or ""
        origin = item.get('tool_origin', 'Interest Panel')
        timestamp = item.get('timestamp', 'N/A')
        data = item.get('data', {}) or {}

        info_rows = []
        if item_type == 'solution':
            genes = data.get('selected_genes', [])
            info_rows.append(html.Li(f"Genes: {len(genes)}"))
            info_rows.append(html.Li(f"Front: {data.get('front_name', 'N/A')}"))
            info_rows.append(html.Li(f"Solution ID: {data.get('solution_id', 'N/A')}"))
            if genes:
                info_rows.append(html.Li(f"Gene list: {', '.join(genes[:30])}" + (" ..." if len(genes) > 30 else "")))
        elif item_type == 'solution_set':
            sols = data.get('solutions', [])
            info_rows.append(html.Li(f"Solutions: {len(sols)}"))
            info_rows.append(html.Li(f"Unique genes: {data.get('unique_genes_count', 'N/A')}"))
        elif item_type == 'gene_set':
            genes = data.get('genes', [])
            info_rows.append(html.Li(f"Genes: {len(genes)}"))
            if genes:
                info_rows.append(html.Li(f"Gene list: {', '.join(genes[:30])}" + (" ..." if len(genes) > 30 else "")))
        elif item_type == 'individual_gene':
            info_rows.append(html.Li(f"Gene: {data.get('gene', 'N/A')}"))
            info_rows.append(html.Li(f"Source: {data.get('source', 'N/A')}"))
        elif item_type == 'combined_gene_group':
            info_rows.append(html.Li(f"Genes: {data.get('gene_count', 0)}"))
            info_rows.append(html.Li(f"Source items: {len(data.get('source_items', []))}"))

        detail = dbc.Card([
            dbc.CardBody([
                html.H5(name, className="fw-bold mb-2"),
                html.Div([
                    dbc.Badge(item_type, color="secondary", className="me-2"),
                    html.Small(f"Origin: {origin}", className="text-muted me-3"),
                    html.Small(f"Added: {timestamp}", className="text-muted")
                ], className="mb-2"),
                html.H6("Details", className="fw-bold small"),
                html.Ul(info_rows if info_rows else [html.Li("No additional data available.", className="text-muted")], className="small"),
                html.H6("Current Comment", className="fw-bold small mt-3"),
                html.Div(comment or "No comment", className="text-muted small")
            ])
        ], className="border-0 shadow-sm")

        # Attachments preview
        attachments = item.get('attachments', []) or []
        att_cards = []
        for att in attachments:
            att_id = att.get('id')
            att_type = att.get('type')
            att_name = att.get('name', att_type)
            att_source = att.get('source', '')
            att_comment = att.get('comment', '')
            include_flag = att.get('include', True)
            payload = att.get('payload', {})

            header = html.Div([
                html.Div([
                    dbc.Badge(att_type or "attachment", color="info", className="me-2"),
                    html.Strong(att_name),
                    html.Span(f" ({att_source})", className="text-muted small ms-1")
                ], className="d-flex align-items-center"),
                dbc.Checklist(
                    options=[{"label": "Include in export", "value": "include"}],
                    value=["include"] if include_flag else [],
                    id={'type': 'export-attachment-include', 'att_id': att_id},
                    switch=True,
                    className="mt-2"
                )
            ])

            body_children = []
            if att_type == 'table':
                cols = payload.get('columns', [])
                rows = payload.get('rows', [])
                safe_rows = []
                for r in rows:
                    safe_row = {}
                    for k, v in r.items():
                        if isinstance(v, (list, tuple)):
                            safe_row[k] = ', '.join([str(x) for x in v])
                        elif isinstance(v, dict):
                            safe_row[k] = json.dumps(v)
                        else:
                            safe_row[k] = v
                    safe_rows.append(safe_row)
                table = dash_table.DataTable(
                    columns=[{"name": c, "id": c, "hideable": True} for c in cols],
                    data=safe_rows,
                    page_size=10,
                    page_action="native",
                    sort_action="none",
                    filter_action="none",
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'border': '1px solid #dee2e6'
                    },
                    style_cell={
                        'fontSize': 12,
                        'padding': '6px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'border': '1px solid #dee2e6'
                    }
                )
                body_children.append(table)
            elif att_type in ['manhattan', 'heatmap']:
                img_b64 = payload.get('image')
                img_error = payload.get('error')
                if img_b64:
                    body_children.append(
                        html.Img(
                            src=img_b64,
                            style={
                                'width': '80%',
                                'maxWidth': '80%',
                                'display': 'block',
                                'margin': '0 auto',
                                'border': '1px solid #ddd',
                                'borderRadius': '4px'
                            }
                        )
                    )
                elif img_error:
                    body_children.append(
                        dbc.Alert(
                            img_error,
                            color="warning",
                            className="small mb-0"
                        )
                    )
                else:
                    body_children.append(
                        dbc.Alert(
                            "No hay imagen guardada en este adjunto (la captura no se generó al adjuntar).",
                            color="light",
                            className="small mb-0"
                        )
                    )
            elif att_type == 'pathway':
                image_url = payload.get('image_url')
                link_url = payload.get('link_url')
                if image_url:
                    img = html.Img(src=image_url, style={'maxWidth': '100%', 'border': '1px solid #ddd', 'borderRadius': '4px'})
                    body_children.append(html.A(img, href=link_url or image_url, target="_blank"))

            body_children.append(html.Div([
                html.Label("Attachment Comment", className="fw-bold small mt-2"),
                dcc.Textarea(
                    id={'type': 'export-attachment-comment', 'att_id': att_id},
                    value=att_comment,
                    style={'minHeight': '80px'},
                    className="form-control"
                )
            ], className="mt-2"))

            att_cards.append(
                dbc.Card([
                    dbc.CardHeader(header),
                    dbc.CardBody(body_children)
                ], className="mb-3")
            )

        attachments_preview = att_cards if att_cards else dbc.Alert("No attachments for this item.", color="light", className="small")

        return detail, attachments_preview, comment

    # Guardar comentario editado
    @app.callback(
        [Output('interest-panel-store', 'data', allow_duplicate=True),
         Output('export-comment-save-status', 'children')],
        Input('export-save-comment-btn', 'n_clicks'),
        [State('export-selected-indices-store', 'data'),
         State('export-comment-editor', 'value'),
         State({'type': 'export-attachment-comment', 'att_id': ALL}, 'value'),
         State({'type': 'export-attachment-comment', 'att_id': ALL}, 'id'),
         State({'type': 'export-attachment-include', 'att_id': ALL}, 'value'),
         State({'type': 'export-attachment-include', 'att_id': ALL}, 'id'),
         State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def save_item_comment(n_clicks, selected_indices, new_comment, att_comments, att_comment_ids, att_includes, att_include_ids, items):
        if not n_clicks:
            raise PreventUpdate
        if not selected_indices or items is None:
            return dash.no_update, dbc.Alert("Select an item first.", color="warning", className="py-1 px-2 mt-2")
        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate

        updated = list(items)
        item = dict(updated[idx])
        item['comment'] = new_comment or ""

        attachments = item.get('attachments', []) or []
        att_comment_map = {}
        for val, cid in zip(att_comments or [], att_comment_ids or []):
            if isinstance(cid, dict):
                att_comment_map[cid.get('att_id')] = val
        att_include_map = {}
        for val, cid in zip(att_includes or [], att_include_ids or []):
            if isinstance(cid, dict):
                att_include_map[cid.get('att_id')] = bool(val)

        new_attachments = []
        for att in attachments:
            att_id = att.get('id')
            att_copy = dict(att)
            if att_id in att_comment_map:
                att_copy['comment'] = att_comment_map[att_id] or ""
            if att_id in att_include_map:
                att_copy['include'] = att_include_map[att_id]
            new_attachments.append(att_copy)
        item['attachments'] = new_attachments

        updated[idx] = item
        status = dbc.Alert("Comment saved.", color="success", className="py-1 px-2 mt-2")
        return updated, status

    # Store para selección única
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

        triggered_value = ctx.triggered[0].get('value', None)
        if triggered_value is None and 0 <= idx < len(checkbox_values):
            triggered_value = checkbox_values[idx]

        if triggered_value:
            return [idx]
        return []

    # Export: PDF
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

    # Export: TXT
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

    # Exportar Pareto CSV
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

    # Exportar Pareto JSON
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

    # Exportar Genes CSV
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

    # Exportar Genes TXT
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

    # Resumen de sesión
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
