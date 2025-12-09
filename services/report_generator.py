# services/report_generator.py

import io
from io import BytesIO
import json
import pandas as pd
import base64
import logging
import math
from datetime import datetime

# Imports para PDF ReportLab
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Imports para Matplotlib Plots (asume que ya están instalados)
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from collections import Counter
try:
    from matplotlib_venn import venn2, venn3
except ImportError:
    pass

logger = logging.getLogger(__name__)


# --- 1. Generación de Gráficos (Auxiliares) ---

def create_pareto_plot_for_pdf(fronts_data, objectives):
    """Create a static Pareto plot figure using Plotly, saved as PNG in a buffer."""
    if not fronts_data or not objectives or len(fronts_data) == 0:
        return None

    x_axis = objectives[0]
    y_axis = objectives[1] if len(objectives) > 1 else objectives[0]
    
    fig = go.Figure()

    colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for idx, front in enumerate(fronts_data):
        df = pd.DataFrame(front["data"])
        
        if x_axis not in df.columns or y_axis not in df.columns:
            continue
            
        color = colors_palette[idx % len(colors_palette)]
        
        fig.add_trace(go.Scatter(
            x=df[x_axis],
            y=df[y_axis],
            mode='lines+markers',
            name=front["name"],
            line=dict(color=color, width=1.5),
            marker=dict(size=8, color=color),
            hovertemplate=None,
            showlegend=True
        ))

    fig.update_layout(
        title=f"Pareto Front: {y_axis.replace('_', ' ').title()} vs {x_axis.replace('_', ' ').title()}",
        xaxis_title=x_axis.replace('_', ' ').title(),
        yaxis_title=y_axis.replace('_', ' ').title(),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=60, r=60, t=60, b=60),
    )
    
    # Render Plotly figure to static image buffer (PNG)
    buffer = BytesIO()
    fig.write_image(buffer, format='png', width=700, height=500, scale=1.5)
    buffer.seek(0)
    return buffer


def create_genes_frequency_chart_for_pdf(all_solutions_list):
    """Create genes frequency chart using Matplotlib, saved as PNG in a buffer."""
    if not all_solutions_list:
        return None

    # Get gene frequency
    all_genes_list = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
    gene_counts_dict = Counter(all_genes_list)
    
    if not gene_counts_dict:
        return None

    # Get top 15 genes
    top_genes_list = sorted(gene_counts_dict.items(), key=lambda x: x[1], reverse=True)[:15]

    if not top_genes_list:
        return None

    top_genes_series = pd.Series(dict(top_genes_list))

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create horizontal bar chart
    ax.barh(top_genes_series.index, top_genes_series.values, color='#4682B4')

    # Add value labels on bars
    for i, (gene, count) in enumerate(top_genes_list):
        percentage = (count / len(all_solutions_list)) * 100 if len(all_solutions_list) > 0 else 0
        y_pos = top_genes_series.index.get_loc(gene)
        ax.text(count + (top_genes_series.values.max() * 0.01), y_pos, f"{count} ({percentage:.1f}%)",
                va='center', ha='left', fontsize=9)

    ax.set_yticks(range(len(top_genes_series)))
    ax.set_yticklabels(top_genes_series.index)
    ax.invert_yaxis() 
    ax.set_xlabel('Frequency (Number of Solutions)', fontsize=12)
    ax.set_title('Most Frequent Genes Across Solutions (Top 15)', fontsize=14, fontweight='bold')

    plt.tight_layout()

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close(fig)

    return img_buffer


# --- 2. Generación del Reporte PDF ---

def generate_pdf_report(data_store, enrichment_data, title="BioPareto Analysis Report"):
    """
    Generates a full PDF report incorporating plots and data.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)
    styles = getSampleStyleSheet()
    story = []

    # Styles
    styles.add(ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=18, alignment=TA_CENTER, spaceAfter=20))
    styles.add(ParagraphStyle(name='Heading1', fontName='Helvetica-Bold', fontSize=14, spaceAfter=12, leftIndent=0))
    styles.add(ParagraphStyle(name='Heading2', fontName='Helvetica-Bold', fontSize=12, spaceAfter=8, leftIndent=10, textColor=colors.blue))
    styles.add(ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, spaceAfter=6, leftIndent=10))
    styles.add(ParagraphStyle(name='Small', fontName='Helvetica', fontSize=8, spaceAfter=4, leftIndent=10))


    # --- Título ---
    story.append(Paragraph(title, styles['TitleStyle']))
    story.append(Paragraph(f"Generation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Small']))
    story.append(Spacer(1, 0.2*inch))


    # --- Sección 1: Data Summary ---
    story.append(Paragraph("1. Data Summary", styles['Heading1']))
    
    fronts = data_store.get('fronts', [])
    main_objectives = data_store.get('main_objectives', ['N/A'])
    
    story.append(Paragraph(f"Total Loaded Fronts: {len(fronts)}", styles['Normal']))
    story.append(Paragraph(f"Main Objectives: {', '.join(main_objectives)}", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    if fronts:
        data_table_content = [['Front Name', 'Solutions', 'Objectives']]
        for front in fronts:
            data_table_content.append([
                front['name'],
                len(front['data']),
                ', '.join(front['objectives'])
            ])

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ])
        
        table = Table(data_table_content, colWidths=[2*inch, 1*inch, 4*inch])
        table.setStyle(table_style)
        story.append(Paragraph("Loaded Front Details:", styles['Heading2']))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))


    # --- Sección 2: Pareto Plot ---
    story.append(Paragraph("2. Pareto Front Visualization", styles['Heading1']))
    
    all_solutions = [s for f in fronts for s in f['data'] if f.get('visible', True)]
    
    if all_solutions and len(main_objectives) >= 2:
        try:
            plot_buffer = create_pareto_plot_for_pdf(fronts, main_objectives)
            if plot_buffer:
                img = Image(plot_buffer, 6.5*inch, 4.5*inch)
                story.append(Paragraph(f"Pareto Plot ({main_objectives[1]} vs {main_objectives[0]}):", styles['Heading2']))
                story.append(img)
                story.append(Spacer(1, 0.3*inch))
            else:
                 story.append(Paragraph("Pareto plot could not be generated.", styles['Normal']))

        except Exception as e:
            logger.error(f"Error generating Pareto plot for PDF: {e}")
            story.append(Paragraph("Error generating Pareto plot.", styles['Normal']))
    else:
        story.append(Paragraph("Not enough data or objectives to generate Pareto plot.", styles['Normal']))

    
    # --- Sección 3: Gene Frequency Analysis ---
    story.append(PageBreak())
    story.append(Paragraph("3. Gene Frequency Analysis", styles['Heading1']))
    
    if all_solutions:
        try:
            chart_buffer = create_genes_frequency_chart_for_pdf(all_solutions)
            if chart_buffer:
                img = Image(chart_buffer, 6.5*inch, 4*inch)
                story.append(Paragraph("Top 15 Gene Frequency:", styles['Heading2']))
                story.append(img)
                story.append(Spacer(1, 0.3*inch))
                
                # Table of 100% genes
                gene_counts = Counter(g for sol in all_solutions for g in sol.get('selected_genes', []))
                total_solutions = len(all_solutions)
                genes_100_percent = [gene for gene, count in gene_counts.items() if count == total_solutions]

                if genes_100_percent:
                    story.append(Paragraph("Genes present in 100% of solutions:", styles['Heading2']))
                    story.append(Paragraph(', '.join(sorted(genes_100_percent)), styles['Normal']))
                else:
                    story.append(Paragraph("No genes found in 100% of solutions.", styles['Normal']))
                
                story.append(Spacer(1, 0.3*inch))

        except Exception as e:
            logger.error(f"Error generating Gene Frequency chart for PDF: {e}")
            story.append(Paragraph("Error generating Gene Frequency chart.", styles['Normal']))

    
    # --- Sección 4: Enrichment Analysis Results (if provided) ---
    if enrichment_data:
        story.append(PageBreak())
        story.append(Paragraph("4. Biological Enrichment Analysis (g:Profiler)", styles['Heading1']))
        
        df = pd.DataFrame(enrichment_data)
        
        if not df.empty:
            # Seleccionar y renombrar columnas para la tabla
            df_table = df[['Source', 'Term', 'P-Value', 'Genes Matched', 'Term Size']].copy()
            
            story.append(Paragraph(f"Results for organism: {df.iloc[0]['Query Size']} genes analyzed.", styles['Normal']))
            story.append(Paragraph(f"Total significant terms (P < 0.05): {len(df_table)}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Formatear la tabla para ReportLab
            data_table_content = [df_table.columns.tolist()] + df_table.values.tolist()
            
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ])
            
            table = Table(data_table_content, colWidths=[1*inch, 3*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(table_style)
            story.append(Paragraph("Significant Terms (P < 0.05):", styles['Heading2']))
            story.append(table)
            story.append(Spacer(1, 0.3*inch))

        else:
            story.append(Paragraph("No significant enrichment results (P < 0.05) were available or found.", styles['Normal']))
            
            
    # --- Final Build ---
    doc.build(story)
    buffer.seek(0)
    return buffer


# --- 3. Reporte PDF de un solo Item (horizontal) ---
def generate_item_pdf(item):
    """Genera un PDF simple para un item del panel de interés en orientación horizontal."""
    if not item:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"Report for {item.get('name','item')}"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ItemTitle', fontName='Helvetica-Bold', fontSize=16, alignment=TA_LEFT, spaceAfter=12))
    styles.add(ParagraphStyle(name='ItemHeading', fontName='Helvetica-Bold', fontSize=12, spaceAfter=8))
    styles.add(ParagraphStyle(name='ItemText', fontName='Helvetica', fontSize=10, spaceAfter=4))

    story = []

    name = item.get('name', 'Item')
    item_type = item.get('type', 'Unknown')
    origin = item.get('tool_origin', 'Interest Panel')
    timestamp = item.get('timestamp', 'N/A')
    comment = item.get('comment', '')
    data = item.get('data', {}) or {}
    attachments = item.get('attachments', []) or []
    validated_sets = data.get('validated_sets', []) or []
    analysis_meta = data.get('analysis_meta', []) or []

    story.append(Paragraph(f"Report: {name}", styles['ItemTitle']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['ItemText']))
    story.append(Paragraph(f"Type: {item_type} | Origin: {origin} | Timestamp: {timestamp}", styles['ItemText']))
    if comment:
        story.append(Paragraph(f"Comment: {comment}", styles['ItemText']))
    story.append(Spacer(1, 0.15 * inch))

    # Resumen segĂşn tipo
    summary_lines = []
    if item_type == 'solution':
        genes = data.get('selected_genes', [])
        summary_lines.append(f"Genes: {len(genes)}")
        summary_lines.append(f"Front: {data.get('front_name', 'N/A')}")
        summary_lines.append(f"Solution ID: {data.get('solution_id', 'N/A')}")
    elif item_type == 'solution_set':
        sols = data.get('solutions', [])
        summary_lines.append(f"Solutions: {len(sols)}")
        summary_lines.append(f"Unique genes: {data.get('unique_genes_count', 'N/A')}")
    elif item_type == 'gene_set':
        genes = data.get('genes', [])
        summary_lines.append(f"Genes: {len(genes)}")
    elif item_type == 'individual_gene':
        summary_lines.append(f"Gene: {data.get('gene', 'N/A')} | Source: {data.get('source', 'N/A')}")
    elif item_type == 'combined_gene_group':
        summary_lines.append(f"Genes: {data.get('gene_count', 0)} | Sources: {len(data.get('source_items', []))}")

    if summary_lines:
        story.append(Paragraph("Summary", styles['ItemHeading']))
        for line in summary_lines:
            story.append(Paragraph(line, styles['ItemText']))
        story.append(Spacer(1, 0.1 * inch))

    # Meta de análisis
    if analysis_meta:
        story.append(Paragraph("Analysis settings", styles['ItemHeading']))
        for am in analysis_meta:
            origin_am = am.get('origin', 'analysis')
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
            line = f"{origin_am} | Organism: {org} | Namespace: {ns} | Validation: {val_txt}"
            if sources:
                line += f" | Sources: {sources}"
            if enabled_opts:
                line += f" | Options: {enabled_opts}"
            if token:
                line += f" | Token: {token}"
            if fireworks_url:
                line += f" | Fireworks: {fireworks_url}"
            story.append(Paragraph(line, styles['ItemText']))
        story.append(Spacer(1, 0.1 * inch))

    # Validated gene sets (solo primer set por namespace ya filtrado aguas arriba)
    if validated_sets:
        story.append(Paragraph("Validated gene sets", styles['ItemHeading']))
        tbl_data = [["Source", "Namespace", "Genes (count)"]]
        for vs in validated_sets:
            source_vs = vs.get('origin', 'analysis')
            ns_vs = vs.get('namespace') or 'N/A'
            genes_vs = vs.get('genes') or []
            tbl_data.append([source_vs, ns_vs, f"{len(genes_vs)}"])
        tbl = Table(tbl_data, colWidths=[2.2 * inch, 1.5 * inch, 2.0 * inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.15 * inch))

    # Adjuntos (incluye tablas renderizadas)
    if attachments:
        # Render de tablas (primeros 50 registros, ya vienen en payload) e imágenes
        for att in attachments:
            att_type = att.get('type')
            if att_type == 'table':
                payload = att.get('payload') or {}
                cols = payload.get('columns') or []
                rows = payload.get('rows') or []
                if not cols or not rows:
                    continue
                # Cada adjunto en página nueva, incluido el primero
                story.append(PageBreak())

                # Celdas con wrapping para evitar traslape
                body_style = ParagraphStyle(name='TblText', fontName='Helvetica', fontSize=8, leading=9, wordWrap='LTR')
                head_style = ParagraphStyle(name='TblHead', fontName='Helvetica-Bold', fontSize=8, leading=9, alignment=1, wordWrap='LTR')
                def wrap_cell(val, head=False):
                    txt = "" if val is None else str(val)
                    return Paragraph(txt, head_style if head else body_style)

                # Encabezados amigables (romper por underscore)
                def header_label(col):
                    if 'intersection_genes' in col:
                        return 'intersection\ngenes'
                    return col.replace('_', '\n')

                header_row = [wrap_cell("No.", head=True)] + [wrap_cell(header_label(c), head=True) for c in cols]
                table_data = [header_row]
                for idx, r in enumerate(rows, start=1):
                    row_vals = [wrap_cell(str(idx))]
                    for c in cols:
                        row_vals.append(wrap_cell(r.get(c, "")))
                    table_data.append(row_vals)
                # Cabecera del adjunto con título y comentario
                story.append(Paragraph(att.get('name', 'Table'), styles['ItemHeading']))
                if att.get('comment'):
                    story.append(Paragraph(att.get('comment'), styles['ItemText']))

                # Ajustar anchos segĂşn nombre de columna para evitar desbordes
                def _compute_col_widths(columns, total_width=10 * inch):
                    weights = [0.6]  # columna del correlativo
                    for c in columns:
                        lc = str(c).lower()
                        if 'intersection_genes' in lc:
                            w = 4.0
                        elif lc == 'term_size':
                            w = 0.9
                        elif 'p_value' in lc:
                            w = 1.0
                        elif 'precision' in lc or 'recall' in lc:
                            w = 1.2
                        elif 'term' in lc or 'description' in lc or 'name' in lc:
                            w = 2.2
                        elif 'source' in lc:
                            w = 0.9
                        else:
                            w = 1.1
                        weights.append(w)
                    if not weights:
                        return None
                    scale = total_width / sum(weights)
                    return [w * scale for w in weights]

                col_widths = _compute_col_widths(cols)
                tbl = Table(table_data, repeatRows=1, colWidths=col_widths)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 0.2 * inch))
            elif att_type in ['manhattan', 'heatmap', 'pathway'] or (att.get('payload') or {}).get('image') or (att.get('payload') or {}).get('image_url'):
                payload = att.get('payload') or {}
                img_b64 = payload.get('image') or payload.get('image_url')
                if not img_b64:
                    continue
                story.append(PageBreak())
                story.append(Paragraph(att.get('name', att_type.title()), styles['ItemHeading']))
                if att.get('comment'):
                    story.append(Paragraph(att.get('comment'), styles['ItemText']))
                try:
                    # limpiar prefijo data URI si existe
                    if img_b64.startswith('data:image'):
                        img_b64 = img_b64.split(',', 1)[1]
                    img_bytes = base64.b64decode(img_b64)
                    img_buf = BytesIO(img_bytes)
                    img = Image(img_buf)
                    img._restrictSize(9 * inch, 6 * inch)
                    story.append(img)
                    link_url = payload.get('link_url')
                    if link_url:
                        story.append(Paragraph(link_url, styles['ItemText']))
                except Exception:
                    story.append(Paragraph("Image could not be rendered.", styles['ItemText']))
    else:
        story.append(Paragraph("No attachments for this item.", styles['ItemText']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- 3. Generación de Reporte TXT ---

def generate_txt_report(data_store, enrichment_data):
    """Generates a plain text report."""
    
    output = io.StringIO()
    
    # Título
    output.write("="*70 + "\n")
    output.write("BIO PARETO ANALYZER REPORT\n")
    output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write("="*70 + "\n\n")

    # Data Summary
    fronts = data_store.get('fronts', [])
    output.write("1. DATA SUMMARY\n")
    output.write("-" * 20 + "\n")
    output.write(f"Total Loaded Fronts: {len(fronts)}\n")
    output.write(f"Main Objectives: {', '.join(data_store.get('main_objectives', ['N/A']))}\n\n")
    
    if fronts:
        output.write("Front Details:\n")
        for front in fronts:
            output.write(f"  - Name: {front['name']} | Solutions: {len(front['data'])} | Objectives: {', '.join(front['objectives'])}\n")
        output.write("\n")
        
    # Gene Frequency Summary
    all_solutions = [s for f in fronts for s in f['data'] if f.get('visible', True)]
    if all_solutions:
        output.write("2. GENE FREQUENCY SUMMARY\n")
        output.write("-" * 25 + "\n")
        gene_counts = Counter(g for sol in all_solutions for g in sol.get('selected_genes', []))
        total_solutions = len(all_solutions)
        
        genes_100_percent = [gene for gene, count in gene_counts.items() if count == total_solutions]
        output.write(f"Total Unique Genes: {len(gene_counts)}\n")
        output.write(f"Genes in 100% of solutions: {len(genes_100_percent)}\n")
        if genes_100_percent:
            output.write(f"  > 100% Genes: {', '.join(sorted(genes_100_percent))}\n")
        output.write("\n")


    # Enrichment Results
    if enrichment_data:
        output.write("3. BIOLOGICAL ENRICHMENT (P < 0.05)\n")
        output.write("-" * 35 + "\n")
        df = pd.DataFrame(enrichment_data)
        
        if not df.empty:
            output.write(f"Analyzed {df.iloc[0]['Query Size']} genes.\n")
            output.write(f"Found {len(df)} significant terms.\n\n")
            
            # Formatear la tabla para TXT
            df_table = df[['Source', 'Term', 'P-Value', 'Genes Matched']].copy()
            df_table.rename(columns={'Genes Matched': 'Matched'}, inplace=True)
            output.write(df_table.to_string(index=False))
            output.write("\n\n")
        else:
            output.write("No significant enrichment results were found.\n\n")

    
    # Final content
    report_content = output.getvalue()
    output.close()
    return report_content


# --- 4. Generación de Archivos Planos (CSV/JSON) ---

def export_pareto_data(data_store, file_format):
    """Exports current Pareto solutions data to JSON or CSV."""
    all_solutions = [s for f in data_store.get('fronts', []) for s in f['data'] if f.get('visible', True)]
    
    if not all_solutions:
        return None

    # Normalizar para incluir todos los objetivos y el front name
    df = pd.json_normalize(all_solutions)
    
    # Limpiar columnas no deseadas o complejas para CSV
    if 'selected_genes' in df.columns:
        df['selected_genes'] = df['selected_genes'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
        
    if file_format == 'csv':
        buffer = BytesIO()
        df.to_csv(buffer, index=False, encoding='utf-8')
        buffer.seek(0)
        return buffer.getvalue().decode('utf-8')
    
    elif file_format == 'json':
        return df.to_json(orient='records', indent=4)
        
    return None

def export_genes_list(data_store, file_format):
    """Exports a unique list of all genes found across all solutions."""
    all_solutions = [s for f in data_store.get('fronts', []) for s in f['data'] if f.get('visible', True)]
    
    if not all_solutions:
        return None
        
    unique_genes = sorted(list(set(g for sol in all_solutions for g in sol.get('selected_genes', []))))
    
    if file_format == 'txt':
        return '\n'.join(unique_genes)
        
    elif file_format == 'csv':
        df = pd.DataFrame({'Gene': unique_genes})
        buffer = BytesIO()
        df.to_csv(buffer, index=False, encoding='utf-8')
        buffer.seek(0)
        return buffer.getvalue().decode('utf-8')

    return None
