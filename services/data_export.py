"""
Data Export Service
"""

import json
import pandas as pd
from datetime import datetime


def export_pareto_to_csv(pareto_data):
    """Export Pareto front data to CSV"""
    all_solutions = []
    for front in pareto_data.get("fronts", []):
        if front.get("visible", True):
            all_solutions.extend(front["data"])
    
    if not all_solutions:
        return None
    
    df = pd.DataFrame(all_solutions)
    return df


def export_pareto_to_json(pareto_data):
    """Export Pareto front data to JSON"""
    all_solutions = []
    for front in pareto_data.get("fronts", []):
        if front.get("visible", True):
            all_solutions.extend(front["data"])
    
    if not all_solutions:
        return None
    
    return json.dumps(all_solutions, indent=2)


def export_genes_to_csv(pareto_data):
    """Export unique genes to CSV"""
    all_solutions = []
    for front in pareto_data.get("fronts", []):
        if front.get("visible", True):
            all_solutions.extend(front["data"])
    
    if not all_solutions:
        return None
    
    all_genes = set([gene for sol in all_solutions for gene in sol.get('selected_genes', [])])
    df = pd.DataFrame({'gene': sorted(all_genes)})
    return df


def export_genes_to_txt(pareto_data):
    """Export unique genes to TXT"""
    all_solutions = []
    for front in pareto_data.get("fronts", []):
        if front.get("visible", True):
            all_solutions.extend(front["data"])
    
    if not all_solutions:
        return None
    
    all_genes = set([gene for sol in all_solutions for gene in sol.get('selected_genes', [])])
    return '\n'.join(sorted(all_genes))
