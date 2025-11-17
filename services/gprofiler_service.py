# services/gprofiler_service.py

"""
Módulo de Servicio para la API de g:Profiler
"""

import requests
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class GProfilerService:
    """
    Clase estática que agrupa los métodos para interactuar con g:Profiler.
    """

    BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"
    CONVERT_URL = "https://biit.cs.ut.ee/gprofiler/api/convert/convert/"

    @staticmethod
    def get_enrichment(gene_list, organism='hsapiens', sources=None):
        """
        Obtiene los resultados de enriquecimiento biológico.
        """
        try:
            if not sources:
                sources = ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]

            logger.debug(f"Solicitando enriquecimiento (g:GOSt) a g:Profiler para {len(gene_list)} genes.")
            
            payload = {
                "organism": organism,
                "query": gene_list,
                "sources": sources,     
                "all_results": True
            }

            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=420)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"Error en la API de g:Profiler (g:GOSt): {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error de conexión con g:Profiler (g:GOSt): {str(e)}")
            return None

    @staticmethod
    def validate_genes(gene_list, organism='hsapiens', target_namespace='HGNC'):
        """
        Valida IDs usando g:Convert. 
        MODIFICADO: Ya no calcula ni retorna la lista de 'unrecognized_probes'.
        """
        if not gene_list:
            return {'validated_genes': [], 'unrecognized_probes': []}
            
        input_gene_set = set(gene_list)

        try:
            logger.debug(f"Validando (g:Convert) {len(input_gene_set)} IDs. Organismo: {organism}")
            
            payload = {
                "organism": organism,
                "target": target_namespace,
                "query": list(input_gene_set),
                "numeric_ns": "skip"
            }

            response = requests.post(GProfilerService.CONVERT_URL, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()
                results = data.get('result', [])
                
                validated_canonical_genes = set()
                
                for item in results:
                    converted_gene = item.get('converted')
                    # Filtrar Nones y N/A
                    if converted_gene and converted_gene != 'N/A' and converted_gene is not None and converted_gene != 'None':
                        validated_canonical_genes.add(converted_gene)

                # MODIFICACIÓN: No calculamos los no reconocidos para ahorrar proceso y limpiar lógica.
                logger.info(f"g:Convert: {len(input_gene_set)} IDs -> {len(validated_canonical_genes)} genes canónicos.")
                
                return {
                    'validated_genes': sorted(list(validated_canonical_genes)),
                    'unrecognized_probes': [] # Retornamos vacío intencionalmente
                }

            else:
                logger.error(f"Error en la API de g:Profiler (g:Convert): {response.status_code}")
                return {'validated_genes': sorted(list(input_gene_set)), 'unrecognized_probes': []}

        except Exception as e:
            logger.error(f"Error de conexión con g:Profiler (g:Convert): {str(e)}")
            return {'validated_genes': sorted(list(input_gene_set)), 'unrecognized_probes': []}


def get_organisms_from_api():
    """Obtiene la lista de organismos."""
    try:
        response = requests.get(GProfilerService.ORGANISMS_URL, timeout=10)
        if response.status_code == 200:
            organisms_data = response.json()
            options = []
            for org in organisms_data:
                display_name = f"{org.get('display_name', org['id'])} ({org['id']})"
                options.append({'label': display_name, 'value': org['id']})
            return sorted(options, key=lambda x: x['label'])
        else:
            return _get_fallback_organisms()
    except Exception as e:
        logger.error(f"Error obteniendo lista de organismos: {e}")
        return _get_fallback_organisms()


def _get_fallback_organisms():
    return [
        {'label': 'Homo sapiens (hsapiens)', 'value': 'hsapiens'},
        {'label': 'Mus musculus (mmusculus)', 'value': 'mmusculus'},
        {'label': 'Rattus norvegicus (rnorvegicus)', 'value': 'rnorvegicus'},
        {'label': 'Danio rerio (drerio)', 'value': 'drerio'},
        {'label': 'Drosophila melanogaster (dmelanogaster)', 'value': 'dmelanogaster'},
        {'label': 'Caenorhabditis elegans (celegans)', 'value': 'celegans'}
    ]