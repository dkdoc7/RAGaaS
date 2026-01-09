import sys
import os
import asyncio
import json

# Add backend path
sys.path.append("/app")

from app.core.fuseki import fuseki_client

async def main():
    print("Debugging Fuseki Graph Content...")
    
    # KB ID found from previous logs
    kb_id = "fe5ef020-a2f7-425d-883d-5f8982c6320c"
    
    # Query to find everything related to "성기훈"
    debug_query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?s ?p ?o ?g
    WHERE {
      GRAPH ?g {
        ?s ?p ?o .
        # Search for string "성기훈" in subject, predicate, or object
        FILTER (
            CONTAINS(STR(?s), "성기훈") || 
            CONTAINS(STR(?o), "성기훈") ||
            (ISLITERAL(?o) && CONTAINS(STR(?o), "성기훈"))
        )
      }
    }
    LIMIT 50
    """
    
    print(f"\nExecuting Debug Query against KB ID: {kb_id}...")
    try:
        results = fuseki_client.query_sparql(kb_id, debug_query)
        bindings = results.get("results", {}).get("bindings", [])
        
        print(f"\n[Debug Results] Found {len(bindings)} triples related to '성기훈':")
        for binding in bindings:
            s = binding.get("s", {}).get("value", "")
            p = binding.get("p", {}).get("value", "")
            o = binding.get("o", {}).get("value", "")
            g = binding.get("g", {}).get("value", "")
            print(f"Graph: {g}\n S: {s}\n P: {p}\n O: {o}\n")
            
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    asyncio.run(main())
