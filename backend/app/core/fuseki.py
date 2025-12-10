"""
Fuseki connection manager for Graph RAG

Handles connection to Apache Jena Fuseki server and provides
SPARQL query/update methods.
"""

from SPARQLWrapper import SPARQLWrapper, JSON, POST, DIGEST
import httpx
from typing import List, Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FusekiManager:
    def __init__(self):
        self.base_url = settings.FUSEKI_URL
        self.admin_endpoint = f"{self.base_url}/$"
        self.auth = ("admin", "admin")  # Fuseki admin credentials
        
    async def create_dataset(self, kb_id: str) -> bool:
        """
        Create a new dataset for a knowledge base in Fuseki
        """
        dataset_name = f"kb_{kb_id}"
        url = f"{self.admin_endpoint}/datasets"
        
        data = {
            "dbName": dataset_name,
            "dbType": "tdb2"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=self.auth,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Created Fuseki dataset: {dataset_name}")
                    return True
                elif response.status_code == 409:
                    logger.info(f"Dataset {dataset_name} already exists")
                    return True
                else:
                    logger.error(f"Failed to create dataset: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error creating Fuseki dataset: {e}")
            return False
    
    async def delete_dataset(self, kb_id: str) -> bool:
        """
        Delete a dataset from Fuseki
        """
        dataset_name = f"kb_{kb_id}"
        url = f"{self.admin_endpoint}/datasets/{dataset_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, auth=self.auth, timeout=30.0)
                
                if response.status_code == 200:
                    logger.info(f"Deleted Fuseki dataset: {dataset_name}")
                    return True
                elif response.status_code == 404:
                    logger.info(f"Dataset {dataset_name} does not exist")
                    return True
                else:
                    logger.error(f"Failed to delete dataset: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting Fuseki dataset: {e}")
            return False
    
    async def dataset_exists(self, kb_id: str) -> bool:
        """
        Check if a dataset exists in Fuseki
        
        Returns:
            True if dataset exists, False otherwise
        """
        dataset_name = f"kb_{kb_id}"
        url = f"{self.admin_endpoint}/datasets"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, auth=self.auth, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    datasets = data.get("datasets", [])
                    
                    # Check if our dataset is in the list
                    for dataset in datasets:
                        if dataset.get("ds.name") == f"/{dataset_name}":
                            return True
                    return False
                else:
                    logger.error(f"Failed to list datasets: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking if dataset exists: {e}")
            return False
    
    def get_sparql_endpoint(self, kb_id: str) -> str:
        """Get the SPARQL endpoint URL for a knowledge base"""
        dataset_name = f"kb_{kb_id}"
        return f"{self.base_url}/{dataset_name}/sparql"
    
    def get_update_endpoint(self, kb_id: str) -> str:
        """Get the SPARQL update endpoint URL for a knowledge base"""
        dataset_name = f"kb_{kb_id}"
        return f"{self.base_url}/{dataset_name}/update"
    
    async def execute_query(self, kb_id: str, sparql_query: str) -> Optional[List[Dict]]:
        """
        Execute a SPARQL SELECT query
        
        Returns:
            List of result bindings, or None on error
        """
        endpoint = self.get_sparql_endpoint(kb_id)
        
        try:
            sparql = SPARQLWrapper(endpoint)
            sparql.setCredentials("admin", "admin")
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            
            results = sparql.query().convert()
            
            if "results" in results and "bindings" in results["results"]:
                return results["results"]["bindings"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            logger.error(f"Query: {sparql_query}")
            return None
    
    async def execute_update(self, kb_id: str, sparql_update: str) -> bool:
        """
        Execute a SPARQL UPDATE query (INSERT, DELETE, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        endpoint = self.get_update_endpoint(kb_id)
        
        try:
            sparql = SPARQLWrapper(endpoint)
            sparql.setCredentials("admin", "admin")
            sparql.setMethod(POST)
            sparql.setQuery(sparql_update)
            
            sparql.query()
            logger.debug(f"Executed SPARQL update successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing SPARQL update: {e}")
            logger.error(f"Update: {sparql_update}")
            return False
    
    async def healthcheck(self) -> bool:
        """Check if Fuseki server is accessible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/$/ping", auth=self.auth, timeout=5.0)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Fuseki healthcheck failed: {e}")
            return False


# Singleton instance
fuseki_manager = FusekiManager()
