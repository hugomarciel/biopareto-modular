# services/gprofiler_service.py (CÓDIGO COMPLETO Y CORREGIDO)

"""
Módulo de Servicio para la API de g:Profiler

Este archivo encapsula toda la lógica de comunicación con 
los endpoints de la API de g:Profiler.
"""

# Se importa 'requests' para realizar solicitudes HTTP a la API.
import requests
# Se importa 'logging' para registrar eventos, errores y mensajes de depuración.
import logging
from collections import defaultdict

# Se configura una instancia de 'logger' específica para este módulo.
# '__name__' asegura que el logger tenga el nombre del archivo (services.gprofiler_service).
logger = logging.getLogger(__name__)


class GProfilerService:
    """
    Clase estática que agrupa los métodos para interactuar con g:Profiler.
    No se necesita instanciar esta clase, se usan sus métodos directamente.
    """

    # URL base para el endpoint de análisis de enriquecimiento funcional (g:GOSt).
    BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    # URL para el endpoint que lista los organismos disponibles.
    ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"
    
    # URL correcta para la API g:Convert (basada en la documentación)
    CONVERT_URL = "https://biit.cs.ut.ee/gprofiler/api/convert/convert/"


    @staticmethod
    def get_enrichment(gene_list, organism='hsapiens', sources=None):
        """
        Obtiene los resultados de enriquecimiento biológico para una lista de genes dada.
        
        Args:
            gene_list (list): La lista de IDs de genes a analizar.
            organism (str): El ID del organismo (ej. 'hsapiens').
            sources (list): Lista de fuentes de datos (ej. ['GO:BP', 'KEGG']).

        Returns:
            dict: El objeto JSON completo de la respuesta de la API (incluyendo 'result' y 'meta').
                  Retorna None si la solicitud falla.
        """
        try:
            # Si no se especifican fuentes, se utiliza una lista por defecto.
            if not sources:
                sources = ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]

            # Registro de depuración (reemplaza a print) con información de la solicitud.
            logger.debug(f"Solicitando enriquecimiento (g:GOSt) a g:Profiler para {len(gene_list)} genes.")
            logger.debug(f"Organismo: {organism}, Fuentes: {sources}") 
            
            # Se construye el 'payload' (cuerpo de la solicitud) en formato JSON.
            payload = {
                "organism": organism,
                "query": gene_list,
                "sources": sources,     
                "all_results": True
            }

            # Se realiza la solicitud POST a la API, con un tiempo de espera (timeout) de 420s.
            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=420)

            # Se verifica si la solicitud fue exitosa (código de estado 200).
            if response.status_code == 200:
                # Se convierte la respuesta JSON en un diccionario de Python.
                data = response.json()
                logger.debug("Respuesta de g:Profiler (g:GOSt) recibida exitosamente.")
                # Se retorna la respuesta completa.
                return data
            else:
                # Si la API devuelve un error (ej. 404, 500), se registra y retorna None.
                logger.error(f"Error en la API de g:Profiler (g:GOSt): {response.status_code} - {response.text}")
                return None

        except Exception as e:
            # Si ocurre un error de red o de timeout, se captura, registra y retorna None.
            logger.error(f"Error de conexión con g:Profiler (g:GOSt): {str(e)}")
            return None

    @staticmethod
    def validate_genes(gene_list, organism='hsapiens', target_namespace='HGNC'):
        """
        Valida y "sanea" una lista de IDs (ej. probes) usando g:Convert.
        Convierte la lista sucia en una lista limpia de símbolos de genes canónicos.

        Args:
            gene_list (list): La lista "sucia" de IDs de genes/probes.
            organism (str): El ID del organismo (ej. 'hsapiens').
            target_namespace (str): El espacio de nombres de destino. 'HGNC' es ideal
                                     para símbolos de genes humanos canónicos (ej. 'TP53').
                                     Usar 'ENSG' para Ensembl IDs.

        Returns:
            dict: Un diccionario con:
                  {'validated_genes': [lista_limpia], 'unrecognized_probes': [lista_no_reconocida]}
                  Retorna {'validated_genes': [], 'unrecognized_probes': []} si falla.
        """
        if not gene_list:
            return {'validated_genes': [], 'unrecognized_probes': []}
            
        # Convertimos la lista de entrada a un set para facilitar la resta
        input_gene_set = set(gene_list)

        try:
            logger.debug(f"Validando (g:Convert) {len(input_gene_set)} IDs. Organismo: {organism}, Target: {target_namespace}")
            
            payload = {
                "organism": organism,
                "target": target_namespace,
                "query": list(input_gene_set), # Enviamos la lista de IDs únicos
                "numeric_ns": "skip" # Ignora IDs puramente numéricos si no se mapean
            }

            response = requests.post(GProfilerService.CONVERT_URL, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()
                results = data.get('result', [])
                
                # Usamos sets para manejar eficientemente los IDs
                validated_canonical_genes = set()
                probes_que_mapearon = set()
                
                # g:Convert devuelve una lista de mapeos
                for item in results:
                    input_probe = item.get('incoming') # El ID de entrada (ej. '2121_at')
                    converted_gene = item.get('converted') # El ID de salida (ej. 'TP53')
                    
                    # --- 🔑 INICIO DE LA CORRECCIÓN 🔑 ---
                    # Se añade "and converted_gene != 'None'" para filtrar el string "None"
                    if converted_gene and converted_gene != 'N/A' and converted_gene is not None and converted_gene != 'None':
                        validated_canonical_genes.add(converted_gene)
                        probes_que_mapearon.add(input_probe)
                    # --- 🔑 FIN DE LA CORRECCIÓN 🔑 ---

                # Los no reconocidos son los que estaban en el input pero no mapearon a nada
                unrecognized_probes_set = input_gene_set - probes_que_mapearon
                
                logger.info(f"g:Convert: {len(input_gene_set)} IDs -> {len(validated_canonical_genes)} genes canónicos. {len(unrecognized_probes_set)} IDs descartados.")
                
                return {
                    'validated_genes': sorted(list(validated_canonical_genes)),
                    'unrecognized_probes': sorted(list(unrecognized_probes_set))
                }

            else:
                logger.error(f"Error en la API de g:Profiler (g:Convert): {response.status_code} - {response.text}")
                # Fallback: si g:Convert falla, intentamos usar la lista original
                return {'validated_genes': sorted(list(input_gene_set)), 'unrecognized_probes': []}

        except Exception as e:
            logger.error(f"Error de conexión con g:Profiler (g:Convert): {str(e)}")
            # Fallback: si hay un error de conexión, usamos la lista original
            return {'validated_genes': sorted(list(input_gene_set)), 'unrecognized_probes': []}


def get_organisms_from_api():
    """
    Obtiene la lista de organismos disponibles desde la API de g:Profiler.
    Esto se usa para poblar el menú desplegable en la UI.
    """
    try:
        # Se realiza una solicitud GET simple para obtener la lista.
        response = requests.get(GProfilerService.ORGANISMS_URL, timeout=10)
        
        # Si la solicitud es exitosa:
        if response.status_code == 200:
            organisms_data = response.json()
            options = []
            # Se itera sobre la lista de organismos...
            for org in organisms_data:
                # ...y se formatea cada uno en el formato que espera dcc.Dropdown (label y value).
                display_name = f"{org.get('display_name', org['id'])} ({org['id']})"
                options.append({'label': display_name, 'value': org['id']})
            # Se retorna la lista de opciones ordenada alfabéticamente.
            return sorted(options, key=lambda x: x['label'])
        else:
            # Si la API falla, se retorna una lista de 'fallback' (emergencia).
            return _get_fallback_organisms()
    except Exception as e:
        # Si hay un error de conexión, se registra y se usa la lista de fallback.
        logger.error(f"Error obteniendo lista de organismos: {e}")
        return _get_fallback_organisms()


def _get_fallback_organisms():
    """
    Retorna una lista estática de organismos comunes.
    Se usa solo si la API de g:Profiler falla, para que la app siga funcionando.
    """
    return [
        {'label': 'Homo sapiens (hsapiens)', 'value': 'hsapiens'},
        {'label': 'Mus musculus (mmusculus)', 'value': 'mmusculus'},
        {'label': 'Rattus norvegicus (rnorvegicus)', 'value': 'rnorvegicus'},
        {'label': 'Danio rerio (drerio)', 'value': 'drerio'},
        {'label': 'Drosophila melanogaster (dmelanogaster)', 'value': 'dmelanogaster'},
        {'label': 'Caenorhabditis elegans (celegans)', 'value': 'celegans'}
    ]