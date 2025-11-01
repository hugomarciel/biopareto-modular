# services/reactome_service.py (CÓDIGO FINAL VERIFICADO CON DOCUMENTACIÓN)

"""
Reactome Pathway Enrichment Analysis Service
SOLUCIÓN DEFINITIVA: Usamos reactome2py.analysis.identifiers(), 
que es la función correcta para una lista de IDs en la versión 3.0.0.
"""

import logging
import json 
import reactome2py.analysis as analysis
import reactome2py.content as content

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content and Analysis Service API via reactome2py."""
    
    DEFAULT_ORGANISM = "Homo sapiens"

    @staticmethod
    def get_reactome_organisms():
        """
        [Mantenido para conservar el fallback que funciona]
        Recupera los organismos disponibles usando reactome2py.content.species(). 
        """
        HOMO_SAPIENS_FALLBACK = [{'label': ReactomeService.DEFAULT_ORGANISM, 'value': ReactomeService.DEFAULT_ORGANISM}]
        
        try:
            logger.info("Fetching Reactome species list using reactome2py.content.species().")
            
            # Usamos content.species()
            species_data = content.species()
            options = []
            
            for species in species_data:
                if species.get('pathwayCounts', 0) > 0:
                     options.append({'label': species['displayName'], 'value': species['displayName']})
            
            if options:
                options.sort(key=lambda x: (x['value'] != 'Homo sapiens', x['value']))
                logger.info(f"Fetched {len(options)} Reactome species with pathways.")
                return options
            else:
                logger.warning("Fetched 0 species with pathways. Applying Homo sapiens fallback.")
                return HOMO_SAPIENS_FALLBACK

        except Exception as e:
            logger.error(f"Error fetching Reactome species with reactome2py: {str(e)}")
            logger.warning("Error fetching species. Applying Homo sapiens fallback.")
            return HOMO_SAPIENS_FALLBACK


    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Executes Reactome pathway enrichment analysis using reactome2py.analysis.identifiers().
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            return []

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        try:
            # 🔑 PASO CLAVE: Convertir la lista de Python a una cadena separada por comas (formato requerido por identifiers)
            ids_string = ','.join(gene_list)
            
            logger.info(f"Starting Reactome enrichment for {len(gene_list)} genes in {organism_name} using analysis.identifiers().")
            
            # 🔑 SOLUCIÓN DEFINITIVA: Llamada a analysis.identifiers
            report_data = analysis.identifiers( 
                ids=ids_string,              # Usamos la cadena de IDs separada por comas
                species=organism_name, 
                projection=False,            # False por defecto, pero puedes cambiarlo
                page_size='999999',          # Aseguramos obtener todos los resultados en una sola página
                p_value='1.0'                # No aplicamos corte de p-value aquí, lo hacemos después.
            )
            
            pathways = report_data.get('pathways', [])
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome.")
            
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
            return mapped_results

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment with reactome2py: {str(e)}")
            return None