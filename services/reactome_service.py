# services/reactome_service.py (CÓDIGO COMPLETO MODIFICADO)

"""
Reactome Pathway Enrichment Analysis Service (Usando reactome2py)
Modificado para aceptar parámetros de Proyección, Enfermedad e Interactores.
"""

import logging
import json 
import requests 
import reactome2py.analysis as analysis 
import base64

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content and Analysis Service API."""
    
    DEFAULT_ORGANISM = "Homo sapiens"
    SPECIES_URL = "https://reactome.org/ContentService/data/species/all"
    DIAGRAM_EXPORTER_BASE_URL = "https://reactome.org/ContentService/exporter/diagram/"

    @staticmethod
    def get_reactome_organisms():
        """
        Obtiene la lista completa de organismos disponibles en Reactome.
        """
        EXTENDED_FALLBACK = [
            {'label': 'Homo sapiens (Human)', 'value': 'Homo sapiens'},
            {'label': 'Mus musculus (Mouse)', 'value': 'Mus musculus'},
            {'label': 'Rattus norvegicus (Rat)', 'value': 'Rattus norvegicus'},
            {'label': 'Danio rerio (Zebrafish)', 'value': 'Danio rerio'},
            {'label': 'Saccharomyces cerevisiae (Yeast)', 'value': 'Saccharomyces cerevisiae'}
        ]
        
        try:
            logger.info(f"Fetching Reactome species list from direct API: {ReactomeService.SPECIES_URL}")
            
            response = requests.get(ReactomeService.SPECIES_URL, timeout=10)
            response.raise_for_status() 
            
            species_data = response.json()
            options = []
            
            for species in species_data:
                display_name = species.get('displayName')
                if display_name:
                     options.append({'label': display_name, 'value': display_name})
            
            if options:
                options.sort(key=lambda x: (x['value'] != 'Homo sapiens', x['value']))
                logger.info(f"Fetched {len(options)} Reactome species. (Success)")
                return options
            else:
                logger.warning("Fetched 0 species via direct API. Applying extended fallback.")
                return EXTENDED_FALLBACK

        except Exception as e:
            logger.error(f"Unexpected error processing Reactome species list: {str(e)}")
            return EXTENDED_FALLBACK

    # --- 🔑 MODIFICACIÓN: Nuevos argumentos para la función ---
    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM, 
                       projection=True, interactors=False, include_disease=False):
        """
        Ejecuta el análisis de enriquecimiento usando reactome2py con opciones avanzadas.
        
        Argumentos Nuevos:
        - projection (bool): Default True (Coincide con Web).
        - interactors (bool): Default False.
        - include_disease (bool): Default False.
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            return {'results': [], 'token': 'N/A', 'organism_used_api': 'N/A', 'organism_selected': organism_name, 'genes_analyzed': 0}

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        ids_string = ','.join(gene_list)

        analysis_token = 'N/A'
        organism_used_api = organism_name
        
        try:
            logger.info(f"SERVICE INPUT DEBUG: Species={organism_name}, Projection={projection}, Interactors={interactors}, Disease={include_disease}")
            
            # --- 🔑 MODIFICACIÓN: Pasamos los parámetros a la librería ---
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=projection,          # Controlado por UI
                interactors=interactors,        # Controlado por UI
                include_disease=include_disease,# Controlado por UI
                page_size='999999',             # Traer todo
                p_value='1.0'                   # Traer todo
            )
            
            analysis_token = report_data.get('token', 'N/A')
            if analysis_token == 'N/A' and 'summary' in report_data and report_data['summary']:
                analysis_token = report_data['summary'].get('token', 'N/A')
            
            if analysis_token == 'N/A':
                 analysis_token = 'REF_' + str(hash(ids_string))[:8] 
            
            if 'resourceSummary' in report_data and report_data['resourceSummary']:
                organism_used_api = report_data['resourceSummary'][0].get('speciesName', organism_name)

            logger.info(f"SERVICE OUTPUT DEBUG: Token: {analysis_token}")
            
            pathways = report_data.get('pathways', [])
            mapped_results = []
            for p in pathways:
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome', 'term_name': p.get('name', 'N/A'), 'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0), 'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 'fdr_value': entities.get('fdr', 1.0)
                })
            
            return {
                'results': mapped_results,
                'token': analysis_token,
                'organism_used_api': organism_used_api, 
                'organism_selected': organism_name,
                'gene_list': gene_list,
                'genes_analyzed': len(gene_list)
            }

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment: {str(e)}")
            return None

    @staticmethod
    def get_diagram_url(pathway_st_id, analysis_token, file_format="png", quality="7"):
        if not pathway_st_id or not analysis_token or analysis_token.startswith('REF_'):
            return "/assets/reactome_placeholder.png" 

        url = (
            f"{ReactomeService.DIAGRAM_EXPORTER_BASE_URL}"
            f"{pathway_st_id}.{file_format}?"
            f"token={analysis_token}"
        )
        if file_format in ["png", "jpg"] and quality:
             url += f"&quality={quality}"
        return url

    @staticmethod
    def get_diagram_image_base64(pathway_st_id, analysis_token, file_format="png", quality=8):
        diagram_url = ReactomeService.get_diagram_url(pathway_st_id, analysis_token, file_format, str(quality))
        try:
            response = requests.get(diagram_url, timeout=20)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'image/png')
                encoded_string = base64.b64encode(response.content).decode('utf-8')
                return f"data:{content_type};base64,{encoded_string}"
            return None
        except Exception:
            return None