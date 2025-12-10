"""
Graph Service for managing RDF triples and SPARQL queries

This service handles:
1. Converting entities/relations to RDF triples
2. Storing triples in Fuseki
3. Multi-hop graph traversal via SPARQL
4. Retrieving related chunks based on graph connections
"""

import logging
from typing import List, Dict, Optional
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from app.core.fuseki import fuseki_manager
from app.services.ner import BLACKLIST

logger = logging.getLogger(__name__)

# Define namespace for our knowledge base
KB = Namespace("http://ragaas.example.org/kb/")


class GraphService:
    def __init__(self):
        pass
    
    async def create_kb_dataset(self, kb_id: str) -> bool:
        """Create a Fuseki dataset for a knowledge base"""
        return await fuseki_manager.create_dataset(kb_id)
    
    async def delete_kb_dataset(self, kb_id: str) -> bool:
        """Delete a Fuseki dataset for a knowledge base"""
        return await fuseki_manager.delete_dataset(kb_id)
    
    def _create_rdf_graph(
        self,
        entities: List[Dict],
        relations: List[Dict],
        chunk_id: str,
        doc_id: str,
        chunk_content: str
    ) -> Graph:
        """
        Convert entities and relations to RDF triples
        
        Args:
            entities: List of entity dicts with id, type, name
            relations: List of relation dicts with subject, predicate, object
            chunk_id: ID of the chunk
            doc_id: ID of the source document
            chunk_content: Text content of the chunk
            
        Returns:
            RDFLib Graph object
        """
        g = Graph()
        g.bind("kb", KB)
        
        # Create chunk node
        chunk_uri = KB[f"chunk_{chunk_id}"]
        g.add((chunk_uri, RDF.type, KB.TextChunk))
        g.add((chunk_uri, KB.content, Literal(chunk_content)))
        g.add((chunk_uri, KB.doc_id, Literal(doc_id)))
        
        # Create entity nodes
        entity_map = {}
        for entity in entities:
            entity_id = entity.get("id", "")
            entity_type = entity.get("type", "Concept")
            entity_name = entity.get("name", "")
            
            # Create UNIQUE entity URI per chunk to prevent cross-chunk linking
            # Use chunk-specific entity ID: chunk_{chunk_id}_{original_entity_id}
            unique_entity_id = f"{chunk_id}_{entity_id}"
            entity_uri = KB[unique_entity_id]
            entity_map[entity_id] = entity_uri  # Map original ID for relations
            
            # Add entity triples
            entity_type_uri = KB[entity_type]
            g.add((entity_uri, RDF.type, entity_type_uri))
            g.add((entity_uri, KB.name, Literal(entity_name)))
            g.add((entity_uri, KB.mentioned_in, chunk_uri))
        
        # Create relation triples
        for relation in relations:
            subject_id = relation.get("subject", "")
            predicate = relation.get("predicate", "related_to")
            object_id = relation.get("object", "")
            
            if subject_id in entity_map and object_id in entity_map:
                subject_uri = entity_map[subject_id]
                object_uri = entity_map[object_id]
                predicate_uri = KB[predicate]
                
                g.add((subject_uri, predicate_uri, object_uri))
        
        return g
    
    async def store_triples(
        self,
        kb_id: str,
        entities: List[Dict],
        relations: List[Dict],
        chunk_id: str,
        doc_id: str,
        chunk_content: str
    ) -> bool:
        """
        Store RDF triples in Fuseki
        
        Args:
            kb_id: Knowledge base ID
            entities: Extracted entities
            relations: Extracted relations
            chunk_id: Chunk identifier
            doc_id: Document identifier
            chunk_content: Text content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if dataset exists, create if not
            dataset_exists = await fuseki_manager.dataset_exists(kb_id)
            if not dataset_exists:
                logger.info(f"Dataset for KB {kb_id} doesn't exist, creating...")
                created = await fuseki_manager.create_dataset(kb_id)
                if not created:
                    logger.error(f"Failed to create dataset for KB {kb_id}")
                    return False
                logger.info(f"Created dataset for KB {kb_id}")
            
            # Create RDF graph
            g = self._create_rdf_graph(entities, relations, chunk_id, doc_id, chunk_content)
            
            # Serialize to N-Triples format (no prefixes, works with INSERT DATA)
            nt_data = g.serialize(format="nt")
            
            # Create SPARQL INSERT query
            sparql_update = f"""
            INSERT DATA {{
                {nt_data}
            }}
            """
            
            # Execute update
            success = await fuseki_manager.execute_update(kb_id, sparql_update)
            
            if success:
                logger.info(f"Stored {len(entities)} entities and {len(relations)} relations for chunk {chunk_id}")
            else:
                logger.error(f"Failed to store triples for chunk {chunk_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing triples: {e}")
            return False
    
    async def search_by_entities(
        self,
        kb_id: str,
        entity_names: List[str],
        max_hops: int = 2,
        expansion_limit: int = 50,
        relation_keywords: List[str] = None
    ) -> List[Dict]:
        """
        Search for chunks related to entities via graph traversal.
        If relation_keywords are provided, filters paths to those matching the keywords.
        
        Args:
            kb_id: Knowledge base ID
            entity_names: List of entity names to search for
            max_hops: Maximum hop distance (1-3)
            expansion_limit: Max number of results
            relation_keywords: Keywords to filter relationships or target nodes
            
        Returns:
            List of dicts with chunk_id and distance
        """
        if not entity_names:
            return []
            

            
        # 2. Relation Keyword Filter (Search by Relation)
        # If keywords exist, we prefer edges/nodes that match them.
        # However, hard filtering might be too strict if synonyms are used.
        # For now, we apply it as a "Look for this IF present" constraint via regex?
        # A safer bet is to use it to FILTER relationships if the query is "Entity + Keyword".
        
        rel_filter_1 = ""
        rel_filter_2 = ""
        rel_filter_3 = ""
        
        if relation_keywords:
            # Construct Regex: (keyword1|keyword2|...)
            # Escape regex special chars if needed
            import re
            safe_kw = [re.escape(k) for k in relation_keywords]
            kw_regex = "|".join(safe_kw)
            
            # Filter logic: The relation name OR object name should match the keyword
            # This allows finding "Entity -(has role)-> RoleName" via "Role" keyword
            # We match against str(?rel) and str(?name) of target
            
            filter_template = f"""
            FILTER (
                regex(str(?rel{{i}}), "{kw_regex}", "i") || 
                regex(str(?name{{i}}), "{kw_regex}", "i")
            )
            """
            
            # Map valid vars for each hop level
            rel_filter_1 = f'FILTER (regex(str(?rel1), "{kw_regex}", "i") || regex(str(?n1), "{kw_regex}", "i"))'
            rel_filter_2 = f'FILTER (regex(str(?rel2), "{kw_regex}", "i") || regex(str(?n2), "{kw_regex}", "i"))'
            rel_filter_3 = f'FILTER (regex(str(?rel3), "{kw_regex}", "i") || regex(str(?n3), "{kw_regex}", "i"))'

        
        # Create VALUES clause for entity names
        values_clause = " ".join([f'"{name}"' for name in entity_names])
        
        # Build multi-hop SPARQL query
        sparql_query = f"""
        PREFIX kb: <http://ragaas.example.org/kb/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?chunk ?distance
        WHERE {{
          {{
            # Direct match (0-hop)
            ?entity kb:name ?name .
            VALUES ?name {{ {values_clause} }}
            ?entity kb:mentioned_in ?chunk .
            BIND(0 AS ?distance)
          }}
        """
        
        # Add 1-hop if max_hops >= 1
        if max_hops >= 1:
            sparql_query += f"""
          UNION
          {{
            # 1-hop
            ?entity kb:name ?name .
            VALUES ?name {{ {values_clause} }}
            ?entity ?rel1 ?e1 .
            
            # Filter by Relation Keywords (if any)
            {rel_filter_1}
            
            ?e1 kb:mentioned_in ?chunk .
            BIND(1 AS ?distance)
          }}
        """
        
        # Add 2-hop if max_hops >= 2
        if max_hops >= 2:
            sparql_query += f"""
          UNION
          {{
            # 2-hop
            ?entity kb:name ?name .
            VALUES ?name {{ {values_clause} }}
            ?entity ?rel1 ?e1 .
            
            # Note: We don't strictly apply relation filter on hop 1 if we are going to hop 2, 
            # unless we want to enforce specific path.
            {rel_filter_1}
            
            ?e1 ?rel2 ?e2 .
            
            {rel_filter_2}
            
            ?e2 kb:mentioned_in ?chunk .
            BIND(2 AS ?distance)
          }}
        """
        
        # Add 3-hop if max_hops >= 3
        if max_hops >= 3:
            sparql_query += f"""
          UNION
          {{
            # 3-hop
            ?entity kb:name ?name .
            VALUES ?name {{ {values_clause} }}
            ?entity ?rel1 ?e1 .
            
            {rel_filter_1}
            
            ?e1 ?rel2 ?e2 .
            
            {rel_filter_2}
            
            ?e2 ?rel3 ?e3 .
            
            {rel_filter_3}
            
            ?e3 kb:mentioned_in ?chunk .
            BIND(3 AS ?distance)
          }}
        """
        
        sparql_query += f"""
        }}
        ORDER BY ?distance
        LIMIT {expansion_limit}
        """
        
        # Log the generated SPARQL query
        logger.info(f"[Graph Search] Generated SPARQL query for entities {entity_names}, keywords={relation_keywords}")
        logger.info(f"[Graph Search] {sparql_query}")
        
        try:
            results = await fuseki_manager.execute_query(kb_id, sparql_query)
            
            if results is None:
                return []
            
            # Parse results
            chunks = []
            for binding in results:
                chunk_uri = binding.get("chunk", {}).get("value", "")
                distance = int(binding.get("distance", {}).get("value", "0"))
                
                # Extract chunk_id from URI (format: kb:chunk_{chunk_id})
                if "chunk_" in chunk_uri:
                    chunk_id = chunk_uri.split("chunk_")[-1]
                    chunks.append({
                        "chunk_id": chunk_id,
                        "distance": distance
                    })
            
            logger.info(f"Found {len(chunks)} chunks via graph search (max_hops={max_hops})")
            return chunks
            
        except Exception as e:
            logger.error(f"Error in graph search: {e}")
            return []
    
    async def get_chunk_entities(self, kb_id: str, chunk_id: str) -> List[Dict]:
        """
        Get all entities mentioned in a specific chunk
        
        Args:
            kb_id: Knowledge base ID
            chunk_id: Chunk identifier
            
        Returns:
            List of entity dicts with type and name
        """
        chunk_uri = f"http://ragaas.example.org/kb/chunk_{chunk_id}"
        
        sparql_query = f"""
        PREFIX kb: <http://ragaas.example.org/kb/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?entity ?type ?name
        WHERE {{
          ?entity kb:mentioned_in <{chunk_uri}> .
          ?entity rdf:type ?type .
          ?entity kb:name ?name .
        }}
        """
        
        try:
            results = await fuseki_manager.execute_query(kb_id, sparql_query)
            
            if results is None:
                return []
            
            entities = []
            for binding in results:
                entity_type = binding.get("type", {}).get("value", "").split("/")[-1]
                entity_name = binding.get("name", {}).get("value", "")
                
                entities.append({
                    "type": entity_type,
                    "name": entity_name
                })
            
            return entities
            
        except Exception as e:
            logger.error(f"Error getting chunk entities: {e}")
            return []


# Singleton instance
graph_service = GraphService()
