# logic/callbacks/export_callbacks.py

import dash
from dash import Output, Input, State, dcc, html, dash_table, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import json
from datetime import datetime
from services.report_generator import (
    generate_pdf_report,
    generate_txt_report,
    export_pareto_data,
    export_genes_list,
    generate_item_pdf,
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
            'solution': ("primary", "bi bi-record-circle-fill text-primary", "Solution"),
            'solution_set': ("info", "bi bi-stack", "Set"),
            'gene_set': ("success", "bi bi-diagram-3", "Gene Group"),
            'individual_gene': ("warning", "bi bi-shield-check", "Gene"),
            'combined_gene_group': ("success", "bi bi-intersect", "Combined")
        }

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            badge_color, icon, badge_text = type_map.get(item_type, ("secondary", "bi bi-file-earmark", "Item"))
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
                                html.I(className=icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
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
            placeholder = dbc.Alert(
                "Select an item from the list above to view its details.",
                color="light",
                className="d-flex align-items-center small mb-0"
            )
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

        attachments = item.get('attachments', []) or []
        analysis_meta = data.get('analysis_meta', []) or []
        attachments = item.get('attachments', []) or []
        validated_sets = data.get('validated_sets', []) or []
        # Solo mostrar conjuntos realmente validados (g:Convert u otro step de validación)
        def _is_validated(vs):
            meta = vs.get('meta') or {}
            return bool(vs.get('genes')) and bool(meta.get('validation') is True or vs.get('validation') is True)
        validated_sets = [vs for vs in validated_sets if _is_validated(vs)]
        converted_genes = data.get('validated_genes') or data.get('gene_list_validated') or []
        if not converted_genes and attachments:
            # Buscar si alg?n adjunto trae la lista validada (p.ej. g:Profiler)
            for att in attachments:
                att_payload = att.get('payload') or {}
                att_genes = att_payload.get('validated_genes') or att_payload.get('gene_list_validated') or []
                if att_genes:
                    converted_genes = att_genes
                    break

        converted_sections = []
        if validated_sets or converted_genes:
            converted_sections.append(
                html.Div(
                    [
                        html.H6("Validated gene sets", className="fw-bold mb-1"),
                        html.Div([
                            html.Small("Source", className="fw-bold text-muted", style={'width': '180px', 'flexShrink': 0}),
                            html.Small("Namespace", className="fw-bold text-muted", style={'width': '140px', 'flexShrink': 0}),
                            html.Small("Sample genes", className="fw-bold text-muted", style={'flex': 1, 'minWidth': 0}),
                            html.Small("Include", className="fw-bold text-muted text-end", style={'width': '140px', 'flexShrink': 0})
                        ], className="d-flex align-items-center gap-2 px-2")
                    ],
                    className="mb-2"
                )
            )

        if validated_sets:
            for vs in validated_sets:
                genes_vs = vs.get('genes') or []
                if not genes_vs:
                    continue
                origin_vs = vs.get('origin', 'analysis')
                ns_vs = vs.get('namespace') or 'N/A'
                origin_color = 'primary' if origin_vs.lower() == 'gprofiler' else 'success' if origin_vs.lower() == 'reactome' else 'info'
                meta_vs = vs.get('meta') or {}
                sample_genes = genes_vs[:5]
                rest_genes = genes_vs[5:]
                collapse_id = {'type': 'validated-collapse', 'origin': origin_vs, 'namespace': ns_vs}
                toggle_id = {'type': 'validated-toggle', 'origin': origin_vs, 'namespace': ns_vs}
                include_flag = bool(vs.get('include', True))
                meta_parts = []
                if meta_vs.get('organism'):
                    meta_parts.append(f"Organism: {meta_vs.get('organism')}")
                if meta_vs.get('validation') is not None:
                    meta_parts.append(f"Validation: {'on' if meta_vs.get('validation') else 'off'}")
                srcs = meta_vs.get('sources') or []
                if srcs:
                    meta_parts.append(f"Sources: {', '.join(srcs)}")
                thr = meta_vs.get('threshold')
                if thr is not None:
                    meta_parts.append(f"P-threshold: {thr}")
                opts = meta_vs.get('options') or {}
                if opts:
                    label_map = {
                        'project_to_human': 'Project to Human',
                        'include_disease': 'Include Disease',
                        'interactors': 'Include Interactors',
                        'projection': 'Project to Human'
                    }
                    enabled_opts = [label_map.get(k, k) for k, v in opts.items() if v]
                    if enabled_opts:
                        meta_parts.append(f"Options: {', '.join(enabled_opts)}")
                meta_text = " | ".join(meta_parts)
                converted_sections.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                dbc.Badge(origin_vs, color=origin_color, className="me-2"),
                                                html.Small(f"{len(genes_vs)} genes", className="text-muted")
                                            ],
                        className="d-flex align-items-center me-2",
                        style={'width': '180px', 'flexShrink': 0}
                    ),
                    html.Div(
                        dbc.Badge(ns_vs, color="secondary"),
                        className="d-flex align-items-center me-2",
                        style={'width': '140px', 'flexShrink': 0}
                    ),
                    html.Div(" | ".join(sample_genes) + (" ..." if rest_genes else ""), className="small text-muted flex-grow-1", style={'minWidth': 0}),
                    html.Div(
                        dbc.Button("Show more", id=toggle_id, color="link", size="sm", className="p-0"),
                        style={'width': '90px', 'textAlign': 'center'}
                    ),
                    html.Div(
                                dbc.Checklist(
                                    options=[{"label": "Include in export", "value": "include"}],
                                    value=["include"] if include_flag else [],
                                    switch=True,
                                    className="ms-2",
                                    id={'type': 'validated-include', 'origin': origin_vs, 'namespace': ns_vs}
                                ),
                        style={'width': '140px', 'textAlign': 'right'}
                    )
                ],
                className="d-flex align-items-center flex-wrap gap-2"
            ),
            className="py-2 px-2"
        ),
        dbc.Collapse(
            html.Div(
                html.P(', '.join(genes_vs), className="small mb-0"),
                className="px-3 pb-2"
            ),
            id=collapse_id,
            is_open=False
        )
    ],
    className="mb-2 border-0 bg-light"
)
                )
        elif converted_genes:
            sample_genes = converted_genes[:5]
            rest_genes = converted_genes[5:]
            collapse_id = {'type': 'validated-collapse', 'origin': 'validated', 'namespace': 'default'}
            toggle_id = {'type': 'validated-toggle', 'origin': 'validated', 'namespace': 'default'}
            include_flag = True
            converted_sections.append(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            dbc.Badge("validated", color="info", className="me-2"),
                                            html.Small(f"{len(converted_genes)} genes", className="text-muted")
                                        ],
                                        className="d-flex align-items-center me-2",
                                        style={'width': '180px', 'flexShrink': 0}
                                    ),
                                    html.Div(
                                        dbc.Badge("default", color="secondary"),
                                        className="d-flex align-items-center me-2",
                                        style={'width': '140px', 'flexShrink': 0}
                                    ),
                                    html.Div(" | ".join(sample_genes) + (" ..." if rest_genes else ""), className="small text-muted flex-grow-1", style={'minWidth': 0}),
                                    html.Div(
                                        dbc.Button("Show more", id=toggle_id, color="link", size="sm", className="p-0"),
                                        style={'width': '90px', 'textAlign': 'center'}
                                    ),
                                    html.Div(
                                    dbc.Checklist(
                                        options=[{"label": "Include in export", "value": "include"}],
                                        value=["include"] if include_flag else [],
                                        switch=True,
                                        className="ms-2",
                                        id={'type': 'validated-include', 'origin': 'validated', 'namespace': 'default'}
                                    ),
                                        style={'width': '140px', 'textAlign': 'right'}
                                    )
                                ],
                                className="d-flex align-items-center flex-wrap gap-2"
                            ),
                            className="py-2 px-2"
                        ),
                        dbc.Collapse(
                            html.Div(
                                html.P(', '.join(converted_genes), className="small mb-0"),
                                className="px-3 pb-2"
                            ),
                            id=collapse_id,
                            is_open=False
                        )
                    ],
                    className="mb-2 border-0 bg-light"
                )
            )

        detail_children = [
            html.H5(name, className="fw-bold mb-2"),
            html.Div([
                dbc.Badge(item_type, color="secondary", className="me-2"),
                html.Small(f"Origin: {origin}", className="text-muted me-3"),
                html.Small(f"Added: {timestamp}", className="text-muted")
            ], className="mb-2"),
            dbc.Alert(comment or "No comment", color="info", className="py-2 px-3 mb-3"),
            html.H6("Details", className="fw-bold small"),
            html.Ul(info_rows if info_rows else [html.Li("No additional data available.", className="text-muted")], className="small")
        ]
        for section in converted_sections:
            detail_children.append(section)

        # Meta de análisis (gprofiler / reactome) siempre visible
        if analysis_meta:
            meta_rows = []
            for am in analysis_meta:
                origin = am.get('origin', 'analysis')
                org = am.get('organism') or ''
                ns = am.get('namespace') or ''
                val = am.get('validation')
                val_txt = "on" if val else "off" if val is not None else "n/a"
                sources = ", ".join(am.get('sources') or [])
                opts = am.get('options') or {}
                opt_labels = {
                    'project_to_human': 'Project to Human',
                    'include_disease': 'Include Disease',
                    'interactors': 'Include Interactors'
                }
                enabled_opts = ", ".join([opt_labels.get(k, k) for k, v in opts.items() if v])
                token = am.get('token')
                fireworks_url = am.get('fireworks_url')
                meta_rows.append(
                    html.Div([
                        html.Strong(origin, className="me-2"),
                        html.Span(f"Organism: {org}", className="me-3"),
                        html.Span(f"Namespace: {ns}", className="me-3"),
                        html.Span(f"Validation: {val_txt}", className="me-3"),
                        html.Span(f"Sources: {sources}", className="me-3") if sources else None,
                        html.Span(f"Options: {enabled_opts}", className="me-3") if enabled_opts else None,
                        html.Span(f"Token: {token}", className="me-3") if token else None,
                        html.A("Fireworks", href=fireworks_url, target="_blank", className="me-3") if fireworks_url else None
                    ], className="small text-muted mb-1")
                )
            detail_children.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Analysis settings", className="fw-bold mb-2"),
                        *meta_rows
                    ]),
                    className="border-0 bg-light mb-2"
                )
            )

        detail = dbc.Card([dbc.CardBody(detail_children)], className="border-0 shadow-sm")

        # Attachments preview
        attachments = item.get('attachments', []) or []
        # Ordenar: tablas primero para que se muestren antes que imágenes/otros
        attachments = sorted(attachments, key=lambda a: 0 if a.get('type') == 'table' else 1)

        # Config de iconos/colores por tipo
        color_map = {
            'table': 'primary',
            'manhattan': 'success',
            'heatmap': 'success',
            'pathway': 'success'
        }
        icon_map = {
            'table': 'bi bi-table',
            'manhattan': 'bi bi-graph-up',
            'heatmap': 'bi bi-grid-3x3-gap',
            'pathway': 'bi bi-diagram-3'
        }
        label_map = {
            'table': 'Table',
            'manhattan': 'Plot',
            'heatmap': 'Plot',
            'pathway': 'Pathway'
        }

        att_cards = []
        for att in attachments:
            att_id = att.get('id')
            att_type = att.get('type')
            att_name = att.get('name', att_type)
            att_source = att.get('source', '')
            att_comment = att.get('comment', '')
            include_flag = att.get('include', True)
            payload = att.get('payload', {})

            att_color = color_map.get(att_type, 'secondary')
            icon_class = icon_map.get(att_type, 'bi bi-paperclip')
            label_text = label_map.get(att_type, 'Attachment')

            collapse_id = {'type': 'export-attachment-collapse', 'att_id': att_id}
            toggle_button = dbc.Button(
                "Hide/Show",
                id={'type': 'export-attachment-toggle', 'att_id': att_id},
                color="secondary",
                outline=True,
                size="sm",
                className="me-0"
            )

            header = html.Div(
                [
                    html.Div(
                        [
                            html.I(className=icon_class, style={'color': f'var(--bs-{att_color})', 'fontSize': '1.1rem'}),
                            dbc.Badge(label_text, color=att_color, className="ms-2"),
                            html.Strong(att_name, className="ms-2"),
                            html.Small(f"({att_source})", className="text-muted ms-1") if att_source else None,
                            toggle_button
                        ],
                        className="d-flex align-items-center flex-wrap gap-2"
                    ),
                    dbc.Checklist(
                        options=[{"label": "Include in export", "value": "include"}],
                        value=["include"] if include_flag else [],
                        id={'type': 'export-attachment-include', 'att_id': att_id},
                        switch=True,
                        className="ms-auto"
                    )
                ],
                className="d-flex align-items-center justify-content-between flex-wrap gap-2"
            )

            body_children = []
            # Comentario editable y destacado primero
            body_children.append(
                dbc.Alert(
                    [
                        html.Label("Attachment comment", className="fw-bold small mb-1"),
                        dcc.Textarea(
                            id={'type': 'export-attachment-comment', 'att_id': att_id},
                            value=att_comment,
                            className="form-control",
                            style={'minHeight': '80px'},
                            placeholder="Add or edit the comment for this attachment..."
                        )
                    ],
                    color="light",
                    className="py-2 px-3 mb-3 border border-primary border-2 shadow-0"
                )
            )

            content_children = []
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
                content_children.append(table)
            elif att_type in ['manhattan', 'heatmap']:
                img_b64 = payload.get('image')
                img_error = payload.get('error')
                if img_b64:
                    content_children.append(
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
                    content_children.append(
                        dbc.Alert(
                            img_error,
                            color="warning",
                            className="small mb-0"
                        )
                    )
                else:
                    content_children.append(
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
                    content_children.append(html.A(img, href=link_url or image_url, target="_blank"))

            body_children.append(
                dbc.Collapse(content_children, id=collapse_id, is_open=False, className="mt-2")
            )

            att_cards.append(
                dbc.Card([
                    dbc.CardHeader(header),
                    dbc.CardBody(body_children)
                ], className="mb-3")
            )

        attachments_preview = att_cards if att_cards else dbc.Alert("No attachments for this item.", color="light", className="small")

        return detail, attachments_preview, comment

    # Descargar PDF del item seleccionado (orientación horizontal)
    @app.callback(
        Output('export-item-pdf-download', 'data'),
        Input('export-download-item-pdf', 'n_clicks'),
        State('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        State('data-store', 'data'),
        State('export-include-pareto', 'value'),
        prevent_initial_call=True
    )
    def download_item_pdf(n_clicks, selected_indices, items, data_store, include_flags):
        if not n_clicks or not selected_indices or not items:
            raise PreventUpdate
        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate
        item = items[idx]
        include_pareto = bool(include_flags)
        pdf_bytes = generate_item_pdf(item, include_pareto=include_pareto, data_store=data_store)
        if not pdf_bytes:
            raise PreventUpdate
        filename = f"{item.get('name','item')}_report.pdf"
        return dcc.send_bytes(pdf_bytes.getvalue(), filename)

    # Guardar include de adjuntos
    @app.callback(
        Output('interest-panel-store', 'data', allow_duplicate=True),
        Input({'type': 'export-attachment-include', 'att_id': ALL}, 'value'),
        State({'type': 'export-attachment-include', 'att_id': ALL}, 'id'),
        State('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def update_attachment_include(values, ids, selected_indices, items):
        if items is None or not selected_indices:
            raise PreventUpdate
        if values is None or ids is None:
            raise PreventUpdate
        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate
        value_map = {}
        for val, cid in zip(values, ids):
            if isinstance(cid, dict):
                value_map[cid.get('att_id')] = bool(val and 'include' in val)
        updated = list(items)
        item = dict(updated[idx])
        atts = []
        for att in item.get('attachments', []) or []:
            a = dict(att)
            if a.get('id') in value_map:
                a['include'] = value_map[a.get('id')]
            atts.append(a)
        item['attachments'] = atts
        updated[idx] = item
        return updated

    # Guardar include de validated gene sets
    @app.callback(
        Output('interest-panel-store', 'data', allow_duplicate=True),
        Input({'type': 'validated-include', 'origin': ALL, 'namespace': ALL}, 'value'),
        State({'type': 'validated-include', 'origin': ALL, 'namespace': ALL}, 'id'),
        State('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def update_validated_include(values, ids, selected_indices, items):
        if items is None or not selected_indices:
            raise PreventUpdate
        if values is None or ids is None:
            raise PreventUpdate
        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate
        include_map = {}
        for val, cid in zip(values, ids):
            if isinstance(cid, dict):
                key = (cid.get('origin'), cid.get('namespace'))
                include_map[key] = bool(val and 'include' in val)
        updated = list(items)
        item = dict(updated[idx])
        data = dict(item.get('data') or {})
        vsets = data.get('validated_sets', []) or []
        for vs in vsets:
            key = (vs.get('origin'), vs.get('namespace'))
            if key in include_map:
                vs['include'] = include_map[key]
        data['validated_sets'] = vsets
        item['data'] = data
        updated[idx] = item
        return updated

    # Toggle para listas validadas (show more)
    @app.callback(
        Output({'type': 'validated-collapse', 'origin': MATCH, 'namespace': MATCH}, 'is_open'),
        Input({'type': 'validated-toggle', 'origin': MATCH, 'namespace': MATCH}, 'n_clicks'),
        State({'type': 'validated-collapse', 'origin': MATCH, 'namespace': MATCH}, 'is_open'),
        prevent_initial_call=True
    )
    def toggle_validated_collapse(n_clicks, is_open):
        if not n_clicks:
            raise PreventUpdate
        return not is_open

    # Guardado de comentario de adjuntos al perder foco
    @app.callback(
        Output('interest-panel-store', 'data', allow_duplicate=True),
        Input({'type': 'export-attachment-comment', 'att_id': ALL}, 'n_blur'),
        State({'type': 'export-attachment-comment', 'att_id': ALL}, 'value'),
        State({'type': 'export-attachment-comment', 'att_id': ALL}, 'id'),
        State('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def autosave_attachment_comment(n_blur_list, values, id_list, selected_indices, items):
        ctx = dash.callback_context
        if items is None or not selected_indices:
            raise PreventUpdate
        if not ctx.triggered:
            raise PreventUpdate

        try:
            trigger_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        except Exception:
            raise PreventUpdate

        att_id = trigger_id.get('att_id')
        if att_id is None:
            raise PreventUpdate

        # Buscar el valor correspondiente en la lista
        value_map = {}
        for val, cid in zip(values or [], id_list or []):
            if isinstance(cid, dict):
                value_map[cid.get('att_id')] = val

        new_value = value_map.get(att_id, "")

        idx_item = selected_indices[0]
        if idx_item >= len(items):
            raise PreventUpdate

        updated_items = list(items)
        item = dict(updated_items[idx_item])
        attachments = item.get('attachments', []) or []
        new_attachments = []
        changed = False
        for att in attachments:
            att_copy = dict(att)
            if att_copy.get('id') == att_id:
                att_copy['comment'] = new_value or ""
                changed = True
            new_attachments.append(att_copy)

        if not changed:
            raise PreventUpdate

        item['attachments'] = new_attachments
        updated_items[idx_item] = item
        return updated_items


    # Toggle mostrar/ocultar cada adjunto
    @app.callback(
        Output({'type': 'export-attachment-collapse', 'att_id': MATCH}, 'is_open'),
        Input({'type': 'export-attachment-toggle', 'att_id': MATCH}, 'n_clicks'),
        State({'type': 'export-attachment-collapse', 'att_id': MATCH}, 'is_open'),
        prevent_initial_call=True
    )
    def toggle_attachment_collapse(n_clicks, is_open):
        if not n_clicks:
            raise PreventUpdate
        return not is_open

    # Auto-guardado del comentario del item principal
    @app.callback(
        Output('interest-panel-store', 'data', allow_duplicate=True),
        Input('export-comment-editor', 'value'),
        State('export-selected-indices-store', 'data'),
        State('interest-panel-store', 'data'),
        prevent_initial_call=True
    )
    def autosave_item_comment(new_comment, selected_indices, items):
        if items is None or not selected_indices:
            raise PreventUpdate
        idx = selected_indices[0]
        if idx >= len(items):
            raise PreventUpdate
        updated = list(items)
        item = dict(updated[idx])
        item['comment'] = new_comment or ""
        updated[idx] = item
        return updated

    # Store para selección única
    @app.callback(
        Output('export-selected-indices-store', 'data'),
        Input({'type': 'export-card-checkbox', 'index': ALL}, 'value'),
        State('export-selected-indices-store', 'data'),
        prevent_initial_call=True
    )
    def enforce_single_selection(checkbox_values, prev_selected):
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

        # Si el render inicial llega con None/[] pero ya había selección previa, la preservamos.
        if (triggered_value is None or triggered_value == []) and prev_selected:
            valid_prev = [i for i in prev_selected if isinstance(i, int)]
            if valid_prev:
                return valid_prev

        if triggered_value:
            return [idx]
        return []

    # Mostrar/ocultar bloque de detalles seg?en selecci?en
    @app.callback(
        Output('export-item-details-wrapper', 'style'),
        Input('export-selected-indices-store', 'data')
    )
    def toggle_item_details_visibility(selected_indices):
        if not selected_indices:
            return {'display': 'none'}
        return {}

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
