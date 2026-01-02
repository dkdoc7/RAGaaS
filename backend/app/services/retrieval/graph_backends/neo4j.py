import logging
from typing import List, Dict, Any
from app.core.neo4j_client import neo4j_client
from .base import GraphBackend

logger = logging.getLogger(__name__)

class Neo4jBackend(GraphBackend):
    """Neo4j implementation of GraphBackend."""

    async def query(
        self,
        kb_id: str,
        entities: List[str],
        hops: int,
        query_type: str,
        relationship_keywords: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute graph query on Neo4j using Cypher.
        
        Args:
            use_relation_filter (bool): If True, filter by relationship keywords for more precise results.
                                        If False, use entity-based traversal for maximum recall.
        """
        use_relation_filter = kwargs.get("use_relation_filter", True)

        if not entities:
            return {"chunk_ids": [], "sparql_query": "", "triples": []}
        
        # Build query based on use_relation_filter setting
        if use_relation_filter and relationship_keywords:
            # Mode 1: Filter by relationship type keywords (more precise, less recall)
            rel_conditions = " OR ".join([f"type(r) CONTAINS '{kw}'" for kw in relationship_keywords])
            cypher_query = f"""
            MATCH (s:Entity)
            WHERE s.name IN $entities
            MATCH path = (s)-[r*1..{hops}]-(o:Entity)
            WHERE ANY(rel IN relationships(path) WHERE {rel_conditions})
            MATCH (o)-[:MENTIONED_IN]->(c:Chunk)
            RETURN DISTINCT c.id as chunk_id, nodes(path) as path_nodes, relationships(path) as path_rels
            LIMIT 100
            """
            print(f"DEBUG: [Neo4j] Using RELATION FILTER mode with keywords: {relationship_keywords}")
        else:
            # Mode 2: Entity-based traversal (maximum recall)
            cypher_query = f"""
            MATCH (s:Entity)
            WHERE s.name IN $entities
            MATCH path = (s)-[*1..{hops}]-(o:Entity)
            MATCH (o)-[:MENTIONED_IN]->(c:Chunk)
            RETURN DISTINCT c.id as chunk_id, nodes(path) as path_nodes, relationships(path) as path_rels
            LIMIT 100
            """
            print(f"DEBUG: [Neo4j] Using ENTITY-ONLY mode (no relation filter)")
        
        # Also try to find chunks directly connected to the queried entities
        # (not just through paths to other entities)
        direct_query = """
        MATCH (s:Entity)-[:MENTIONED_IN]->(c:Chunk)
        WHERE s.name IN $entities
        RETURN DISTINCT c.id as chunk_id
        LIMIT 50
        """

        print(f"DEBUG: Executing Neo4j Query: {cypher_query}")
        
        try:
            # Get chunks through entity paths
            records = neo4j_client.execute_query(cypher_query, {"entities": entities})
            chunk_ids = [record["chunk_id"] for record in records]
            
            # Also get directly connected chunks
            direct_records = neo4j_client.execute_query(direct_query, {"entities": entities})
            for record in direct_records:
                chunk_ids.append(record["chunk_id"])
            
            chunk_ids = list(set(chunk_ids))  # Deduplicate
            print(f"DEBUG: Found {len(chunk_ids)} chunks from graph (path: {len(records)}, direct: {len(direct_records)})")
            
            # Get triples that contributed to chunk discovery
            triples = []
            if chunk_ids:
                triples = self._fetch_relevant_triples(chunk_ids)

            return {
                "chunk_ids": chunk_ids,
                "sparql_query": cypher_query,
                "triples": triples
            }
            
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return {"chunk_ids": [], "sparql_query": cypher_query, "triples": []}

    def _fetch_relevant_triples(self, chunk_ids: List[str]) -> List[Dict[str, str]]:
        """Fetch triples connected to the discovered chunks for metadata display."""
        triples = []
        try:
            triples_query = """
            MATCH (s:Entity)-[r:RELATION]->(o:Entity)
            WHERE (s)-[:MENTIONED_IN]->(:Chunk {id: $chunk_id}) 
                OR (o)-[:MENTIONED_IN]->(:Chunk {id: $chunk_id})
            RETURN DISTINCT s.name as subj, r.type as pred, o.name as obj
            LIMIT 10
            """
            
            seen_triples = set()
            for chunk_id in chunk_ids[:5]:  # Limit to first 5 chunks to avoid too many queries
                try:
                    t_records = neo4j_client.execute_query(triples_query, {"chunk_id": chunk_id})
                    for r in t_records:
                        triple_key = (r["subj"], r["pred"], r["obj"])
                        if triple_key not in seen_triples:
                            seen_triples.add(triple_key)
                            triples.append({
                                "subject": r["subj"], 
                                "predicate": r["pred"], 
                                "object": r["obj"]
                            })
                except Exception as e:
                    logger.warning(f"Error fetching triples for chunk {chunk_id}: {e}")
            
            print(f"DEBUG: Found {len(triples)} relevant triples from discovered chunks")
        except Exception as e:
            logger.error(f"Error in _fetch_relevant_triples: {e}")
        
        return triples
