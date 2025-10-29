# services/gprofiler_service.py

"""
gProfiler API Service
"""

import requests
import logging

logger = logging.getLogger(__name__)


class GProfilerService:
    """Service to connect with g:Profiler API"""

    BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"

    @staticmethod
    def get_enrichment(gene_list, organism='hsapiens'):
        """
        Get biological enrichment for a gene list
        """
        try:
            payload = {
                "organism": organism,
                "query": gene_list,
                "sources": ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]
            }

            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    return data['result']
                else:
                    return []
            else:
                logger.error(f"Error in g:Profiler API: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error connecting with g:Profiler: {str(e)}")
            return None


def get_organisms_from_api():
    """Fetch available organisms from gProfiler API"""
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
        logger.error(f"Error fetching organisms: {e}")
        return _get_fallback_organisms()


def _get_fallback_organisms():
    """Fallback organism list"""
    return [
        {'label': 'Homo sapiens (hsapiens)', 'value': 'hsapiens'},
        {'label': 'Mus musculus (mmusculus)', 'value': 'mmusculus'},
        {'label': 'Rattus norvegicus (rnorvegicus)', 'value': 'rnorvegicus'},
        {'label': 'Danio rerio (drerio)', 'value': 'drerio'},
        {'label': 'Drosophila melanogaster (dmelanogaster)', 'value': 'dmelanogaster'},
        {'label': 'Caenorhabditis elegans (celegans)', 'value': 'celegans'}
    ]