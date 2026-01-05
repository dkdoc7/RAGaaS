from typing import List, Dict, Any, Optional
import logging
import os
import shutil
import uuid
import json
from pathlib import Path
from app.core.config import settings
from app.core.milvus import connect_milvus, create_collection
from app.services.embedding import embedding_service
from pymilvus import Collection

logger = logging.getLogger(__name__)

class Doc2OntoProcessor:
    """
    Wrapper for the Doc2Onto pipeline.
    This class interfaces with the Doc2Onto logic to extract graph elements
    and load them into Fuseki or Neo4j (based on graph_backend) and Milvus (Vectors).
    """
    def __init__(self):
        self.client = None
        self.enabled = False
        
        if hasattr(settings, 'DOC2ONTO_CONFIG_PATH') and settings.DOC2ONTO_CONFIG_PATH and os.path.exists(settings.DOC2ONTO_CONFIG_PATH):
            try:
                from doc2onto.api import Doc2OntoClient
                self.client = Doc2OntoClient(config_path=settings.DOC2ONTO_CONFIG_PATH)
                
                # MONKEY MATCH: Force usage of OpenAIExtractor if config specifies gpt models
                # The library v0.1.0 defaults to Stub, so we must swap it manually.
                try:
                    from doc2onto.extractors.openai_extractor import OpenAIExtractor
                    config = self.client.config.extraction
                    if "gpt" in config.llm_model.lower():
                        print(f"[Doc2Onto] Swapping Extractor to OpenAIExtractor (Model: {config.llm_model})")
                        real_extractor = OpenAIExtractor(
                             confidence_threshold=config.confidence_threshold,
                             llm_endpoint=config.llm_endpoint,
                             llm_model=config.llm_model,
                             api_key=settings.OPENAI_API_KEY,
                             examples_path=config.examples_path
                        )
                        self.client._extractor = real_extractor
                except Exception as ex:
                    print(f"[Doc2Onto] Failed to swap extractor: {ex}")

                self.enabled = True
                print(f"[Doc2Onto] Initialized with config: {settings.DOC2ONTO_CONFIG_PATH}")
            except ImportError:
                print("[Doc2Onto] Library not found. Integration disabled.")
            except Exception as e:
                print(f"[Doc2Onto] Failed to initialize: {e}")
        else:
            print("[Doc2Onto] DOC2ONTO_CONFIG_PATH not set or file not found. Integration disabled.")

    async def process_document_full(
        self, 
        file_path: str, 
        kb_id: str, 
        doc_id: str,
        graph_backend: str = "ontology",
        chunking_strategy: str = "size"
    ) -> Dict[str, Any]:
        """
        Process document using the full Doc2Onto pipeline.
        """
        if not self.enabled or not self.client:
            print(f"[Doc2Onto] Disabled. Skipping document {doc_id}")
            return {"status": "skipped", "reason": "disabled"}

        run_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(os.getcwd(), "doc2onto_out", kb_id, doc_id)
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            temp_input_dir = os.path.join(output_dir, "input")
            os.makedirs(temp_input_dir, exist_ok=True)
            
            dest_path = os.path.join(temp_input_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            
            print(f"[Doc2Onto] Starting pipeline for {doc_id} (backend={graph_backend}, run_id={run_id})...")
            
            # Note: Doc2Onto build might need configuration for chunking strategy if supported
            result = self.client.build(
                input_dir=temp_input_dir,
                output_dir=output_dir,
                run_id=run_id
            )
            print(f"[Doc2Onto] Pipeline completed. Stats: {result}")
            
            if graph_backend == "neo4j":
                await self._load_to_neo4j(output_dir, kb_id, doc_id)
                # RAGaaS: Create Entity-Chunk connections after Doc2Onto loads triples
                await self._link_entities_to_chunks(output_dir, kb_id, doc_id)
            else:
                await self._load_to_fuseki(output_dir, kb_id)
            
            chunks_path = os.path.join(output_dir, "chunks.jsonl")
            if os.path.exists(chunks_path):
                await self._load_chunks_to_milvus_adapter(chunks_path, kb_id, doc_id)
                
            return {"status": "success", "result": result}

        except Exception as e:
            print(f"[Doc2Onto] Error processing document {doc_id}: {e}")
            raise e
        finally:
            if os.path.exists(output_dir):
                # shutil.rmtree(output_dir, ignore_errors=True)
                pass

    async def _load_to_fuseki(self, output_dir: str, kb_id: str):
        from doc2onto.loaders import FusekiLoader
        
        base_trig = os.path.join(output_dir, "base.trig")
        evidence_trig = os.path.join(output_dir, "evidence.trig")
        
        fuseki_loader = FusekiLoader(endpoint=settings.FUSEKI_URL, dataset=kb_id)
        
        print(f"[Doc2Onto] Uploading to Fuseki dataset: {kb_id}")
        if os.path.exists(base_trig):
            res = fuseki_loader.upload(base_trig)
            if not res.get("success"):
                print(f"[Doc2Onto] Failed to upload base graph: {res.get('message')}")
        
        if os.path.exists(evidence_trig):
            res = fuseki_loader.upload(evidence_trig)
            if not res.get("success"):
                print(f"[Doc2Onto] Failed to upload evidence graph: {res.get('message')}")

    async def _load_to_neo4j(self, output_dir: str, kb_id: str, doc_id: str):
        """Load extracted triples to Neo4j using Doc2Onto's CLI load command."""
        import subprocess
        
        print(f"[Doc2Onto] Loading to Neo4j using Doc2Onto CLI load command...")
        
        try:
            # Use Doc2Onto CLI load command for Neo4j loading
            cmd = [
                "python3", "-m", "doc2onto.cli", "load",
                "--in", output_dir,
                "--backend", "neo4j",
                "--neo4j", settings.NEO4J_URI,
                "--neo4j-user", settings.NEO4J_USER,
                "--neo4j-password", settings.NEO4J_PASSWORD
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                print(f"[Doc2Onto] Neo4j load completed successfully")
                if result.stdout:
                    print(f"[Doc2Onto] Output: {result.stdout}")
            else:
                print(f"[Doc2Onto] Neo4j load failed with code {result.returncode}")
                print(f"[Doc2Onto] Error: {result.stderr}")
                raise Exception(f"CLI load failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"[Doc2Onto] Neo4j load timed out")
            raise
        except Exception as e:
            print(f"[Doc2Onto] Neo4j load error: {e}")
            raise

    async def _link_entities_to_chunks(self, output_dir: str, kb_id: str, doc_id: str):
        """Create Entity-Chunk connections in Neo4j (RAGaaS responsibility).
        
        Doc2Onto stores entities and triples, but RAGaaS needs to link them
        to chunks for retrieval purposes.
        """
        from app.core.neo4j_client import neo4j_client
        
        candidates_path = os.path.join(output_dir, "candidates_filtered.jsonl")
        if not os.path.exists(candidates_path):
            print(f"[RAGaaS] No candidates file for entity-chunk linking")
            return
        
        print(f"[RAGaaS] Creating Entity-Chunk connections...")
        
        # Collect entities and their source chunks
        entity_chunks = {}  # entity_name -> set of chunk_ids
        
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                
                # Extract entities from triples
                for triple in record.get("triples", []):
                    source_chunk_id = triple.get("source_chunk_id", "")
                    
                    # Extract chunk index from source_chunk_id (e.g., "doc|v1|0000" -> 0)
                    if isinstance(source_chunk_id, str) and '|' in source_chunk_id:
                        try:
                            chunk_idx = int(source_chunk_id.split('|')[-1])
                        except ValueError:
                            chunk_idx = 0
                    else:
                        chunk_idx = source_chunk_id if isinstance(source_chunk_id, int) else 0
                    
                    # Milvus-compatible chunk_id
                    chunk_id = f"{doc_id}_{chunk_idx}"
                    
                    # Track subject and object entities
                    for entity in [triple.get("subject", ""), triple.get("object", "")]:
                        if entity:
                            if entity not in entity_chunks:
                                entity_chunks[entity] = set()
                            entity_chunks[entity].add(chunk_id)
        
        print(f"[RAGaaS] Found {len(entity_chunks)} entities to link to chunks")
        
        # Create Chunk nodes and MENTIONED_IN relationships
        count = 0
        for entity_name, chunk_ids in entity_chunks.items():
            for chunk_id in chunk_ids:
                # Create Chunk node and MENTIONED_IN relationship
                # Match entity by label_ko (Doc2Onto schema, 언더스코어 변환 포함)
                cypher = """
                MERGE (c:Chunk {id: $chunk_id})
                ON CREATE SET c.kb_id = $kb_id
                WITH c
                MATCH (e:Entity)
                WHERE e.label_ko = $entity_name 
                   OR e.label_ko = $entity_name_underscore
                   OR e.name = $entity_name
                MERGE (e)-[:MENTIONED_IN]->(c)
                """
                
                # Doc2Onto uses underscores in some cases
                entity_name_underscore = entity_name.replace(" ", "_")
                
                params = {
                    "chunk_id": chunk_id,
                    "kb_id": kb_id,
                    "entity_name": entity_name,
                    "entity_name_underscore": entity_name_underscore
                }
                
                try:
                    neo4j_client.execute_query(cypher, parameters=params)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to link entity '{entity_name}' to chunk: {e}")
        
        print(f"[RAGaaS] Created {count} Entity-Chunk connections")

    async def _load_to_neo4j_legacy(self, output_dir: str, kb_id: str, doc_id: str):
        """Neo4j loading using APOC for dynamic relationship types."""
        from app.core.neo4j_client import neo4j_client
        
        candidates_path = os.path.join(output_dir, "candidates_filtered.jsonl")
        if not os.path.exists(candidates_path):
            print(f"[Doc2Onto] No candidates file found")
            return
        
        if not neo4j_client.verify_connectivity():
            print(f"[Doc2Onto] Neo4j connection failed. Check credentials.")
            return
        
        print(f"[Doc2Onto] Loading triples to Neo4j with dynamic relation types...")
        
        triples = []
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                for triple in record.get("triples", []):
                    triples.append({
                        "subject": triple.get("subject", ""),
                        "predicate": triple.get("predicate", ""),
                        "object": triple.get("object", ""),
                        "chunk_id": triple.get("source_chunk_id", 0)
                    })
        
        print(f"[Doc2Onto] Found {len(triples)} triples to insert")
        
        count = 0
        for triple in triples:
            source_chunk_id = triple['chunk_id']  # e.g., "debug_squid_game|v1|0000"
            
            # Extract chunk index from source_chunk_id
            # Format: "doc_name|version|chunk_idx" -> extract last part as int
            if isinstance(source_chunk_id, str) and '|' in source_chunk_id:
                try:
                    chunk_idx = int(source_chunk_id.split('|')[-1])
                except ValueError:
                    chunk_idx = 0
            else:
                chunk_idx = source_chunk_id if isinstance(source_chunk_id, int) else 0
            
            # Match Milvus chunk_id format: {doc_id}_{chunk_idx}
            chunk_id = f"{doc_id}_{chunk_idx}"
            
            # Use APOC to create dynamic relationship type
            # This allows relation types like "제자", "스승" instead of fixed "RELATION"
            cypher = """
            MERGE (s:Entity {name: $subj})
            ON CREATE SET s.kb_id = $kb_id
            MERGE (o:Entity {name: $obj})
            ON CREATE SET o.kb_id = $kb_id
            WITH s, o
            CALL apoc.create.relationship(s, $pred, {}, o) YIELD rel
            WITH s, o
            MERGE (c:Chunk {id: $chunk_id})
            ON CREATE SET c.kb_id = $kb_id
            MERGE (s)-[:MENTIONED_IN]->(c)
            MERGE (o)-[:MENTIONED_IN]->(c)
            """
            
            params = {
                "subj": triple["subject"],
                "obj": triple["object"],
                "pred": triple["predicate"],
                "chunk_id": chunk_id,
                "kb_id": kb_id
            }
            
            try:
                neo4j_client.execute_query(cypher, parameters=params)
                count += 1
            except Exception as e:
                print(f"[Doc2Onto] Failed to insert triple: {e}")

        print(f"[Doc2Onto] Inserted {count} triples to Neo4j")

    async def _load_chunks_to_milvus_adapter(self, jsonl_path: str, kb_id: str, doc_id: str):
        print(f"[Doc2Onto] Loading chunks to Milvus for KB: {kb_id}")
        
        try:
            connect_milvus()
            collection = create_collection(kb_id)
        except Exception as e:
            print(f"[Doc2Onto] Failed to connect/create Milvus collection: {e}")
            return

        batch_texts = []
        batch_metadatas = []
        batch_chunk_ids = []
        
        with open(jsonl_path, "r", encoding="utf-8") as f:
            # First pass: read all lines to get correct IDs/metadata
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                record = json.loads(line)
                
                text = record.get("text", "")
                if not text:
                    continue
                
                # Use provided chunk_idx or loop index
                chunk_idx = record.get("chunk_idx", i)
                chunk_id = f"{doc_id}_{chunk_idx}"
                
                metadata = {
                    "original_chunk_id": record.get("chunk_id"), # keep raw id in metadata
                    "chunk_idx": chunk_idx,
                    "section_path": record.get("section_path"),
                    "doc_ver": record.get("doc_ver"),
                    "source": "doc2onto"
                }
                
                batch_texts.append(text)
                batch_metadatas.append(metadata)
                batch_chunk_ids.append(chunk_id)

        if not batch_texts:
            print("[Doc2Onto] No chunks found to load to Milvus.")
            return

        try:
            embeddings = await embedding_service.get_embeddings(batch_texts)
        except Exception as e:
            print(f"[Doc2Onto] Failed to generate embeddings: {e}")
            return

        insert_data = [
            [doc_id] * len(batch_texts),
            batch_chunk_ids,
            batch_texts,
            batch_metadatas,
            embeddings
        ]
        
        try:
            res = collection.insert(insert_data)
            collection.flush()
            print(f"[Doc2Onto] Inserted {len(batch_texts)} chunks into Milvus")
        except Exception as e:
            print(f"[Doc2Onto] Failed to insert into Milvus: {e}")
            raise e

    async def process(self, text: str, chunk_id: str, **kwargs) -> Dict[str, Any]:
        """
        Legacy process method compatible with IngestionService's hybrid approach if needed.
        Currently returns empty to indicate Doc2Onto pipeline should be used via process_document_full.
        """
        print("[Doc2Onto] Legacy process called. returning empty.")
        return {"triples": [], "entities": []}

doc2onto_processor = Doc2OntoProcessor()
