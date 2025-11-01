# services/reactome_service.py (SOLUCIÓN HÍBRIDA FINAL Y EXTENDIDA)

"""
Reactome Pathway Enrichment Analysis Service
SOLUCIÓN FINAL: Utiliza requests para obtener la lista de especies (reparando el filtro) 
y mantiene reactome2py para el análisis de enriquecimiento funcional.
"""

import logging
import json 
import requests 
import reactome2py.analysis as analysis 

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content and Analysis Service API via reactome2py."""
    
    DEFAULT_ORGANISM = "Homo sapiens"
    
    # 🔑 URL API Directa para obtener todas las especies (la misma que usaste en el ejemplo funcional)
    SPECIES_URL = "https://reactome.org/ContentService/data/species/all"

    @staticmethod
    def get_reactome_organisms():
        """
        Obtiene la lista completa de organismos disponibles en Reactome utilizando la API directa (requests).
        Garantiza el fallback extendido con 5 organismos modelo comunes.
        """
        # 🔑 FALLBACK EXTENDIDO FINAL CON 5 ESPECIES MODELO 🔑
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
            response.raise_for_status() # Lanza excepción para códigos 4xx/5xx
            
            species_data = response.json()
            options = []
            
            for species in species_data:
                # 🔑 REPARACIÓN: Usamos la lógica simple que sabes que funcionaba: solo verificamos displayName.
                display_name = species.get('displayName')
                
                if display_name:
                     options.append({'label': display_name, 'value': display_name})
            
            if options:
                # Si se obtiene una lista, la ordenamos, priorizando Homo sapiens
                options.sort(key=lambda x: (x['value'] != 'Homo sapiens', x['value']))
                logger.info(f"Fetched {len(options)} Reactome species. (Success)")
                return options
            else:
                logger.warning("Fetched 0 species via direct API. Applying extended fallback.")
                return EXTENDED_FALLBACK

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Reactome API for species list: {str(e)}")
            logger.warning("Connection error fetching species. Applying extended fallback.")
            return EXTENDED_FALLBACK
        except Exception as e:
            logger.error(f"Unexpected error processing Reactome species list: {str(e)}")
            logger.warning("Processing error fetching species. Applying extended fallback.")
            return EXTENDED_FALLBACK

    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Ejecuta el análisis de enriquecimiento y retorna los resultados y metadatos.
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            # Retornar una estructura vacía con metadatos si no hay genes para analizar
            return {'results': [], 'token': 'N/A', 'organism_used': organism_name, 'genes_analyzed': 0}

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        try:
            logger.info(f"Starting Reactome enrichment for {len(gene_list)} genes in {organism_name} using analysis.identifiers().")
            
            # Esta parte usa reactome2py.analysis, que funciona para el análisis.
            ids_string = ','.join(gene_list)
            
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=False,            
                page_size='999999',          
                p_value='1.0'                
            )
            
            pathways = report_data.get('pathways', [])
            
            # 🔑 NUEVO: Extraer metadatos clave del reporte 🔑
            # El token debe estar en el nivel superior del JSON del reporte
            analysis_token = report_data.get('token', 'N/A')
            organism_used = organism_name # Usamos el nombre enviado, que Reactome valida
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome. Token: {analysis_token}")
            
            # Mapeo a un formato de resultados simplificado y usable
            mapped_results = []
            for p in pathways:
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome',
                    'term_name': p.get('name', 'N/A'),
                    'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0),
                    'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 
                    'fdr_value': entities.get('fdr', 1.0)
                })
                
            logger.info(f"Final mapped results count: {len(mapped_results)}")
            
            # 🔑 RETORNA EL DICCIONARIO COMPLETO con metadatos 🔑
            return {
                'results': mapped_results,
                'token': analysis_token,
                'organism_used': organism_used,
                'genes_analyzed': len(gene_list)
            }

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment with reactome2py: {str(e)}")
            return None