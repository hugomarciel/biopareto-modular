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
            print(f"\n[DEBUG GPROFILER SERVICE] Requesting enrichment for {len(gene_list)} genes")
            print(f"[DEBUG GPROFILER SERVICE] Organism: {organism}")
            print(f"[DEBUG GPROFILER SERVICE] First 5 genes: {gene_list[:5]}")
            
            payload = {
                "organism": organism,
                "query": gene_list,
                "sources": ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]
            }

            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                
                print(f"[DEBUG GPROFILER SERVICE] Response received successfully")
                print(f"[DEBUG GPROFILER SERVICE] Response keys: {list(data.keys())}")
                
                if 'result' in data and data['result']:
                    print(f"[DEBUG GPROFILER SERVICE] Number of results: {len(data['result'])}")
                    
                    if data['result']:
                        first_result = data['result'][0]
                        print(f"[DEBUG GPROFILER SERVICE] First result keys: {list(first_result.keys())}")
                        print(f"[DEBUG GPROFILER SERVICE] FULL FIRST RESULT:")
                        for key, value in first_result.items():
                            if isinstance(value, list) and len(value) > 10:
                                print(f"  - {key}: [{len(value)} items] First 3: {value[:3]}")
                            else:
                                print(f"  - {key}: {value}")
                        print(f"[DEBUG GPROFILER SERVICE] First result 'intersections' field: {first_result.get('intersections', 'KEY NOT FOUND')[:10] if isinstance(first_result.get('intersections'), list) else first_result.get('intersections')}")
                        print(f"[DEBUG GPROFILER SERVICE] First result 'intersection' field: {first_result.get('intersection', 'KEY NOT FOUND')[:10] if isinstance(first_result.get('intersection'), list) else first_result.get('intersection')}")
                    
                    return data['result']
                else:
                    print(f"[DEBUG GPROFILER SERVICE] No results found in response")
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
