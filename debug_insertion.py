import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.core.fuseki import fuseki_client

KB_ID = "09e9662c-e3ed-412c-98b8-dc73dd3a9745"

TRIPLES = [
    '<http://rag.local/entity/Duke> <http://rag.local/relation/is_master_of> <http://rag.local/entity/Jang_Pung> .',
    '<http://rag.local/entity/Duke> <http://www.w3.org/2000/01/rdf-schema#label> "Duke" .',
    '<http://rag.local/entity/Jang_Pung> <http://rag.local/relation/taught_to> <http://rag.local/entity/Oh_Il_Nam> .',
    '<http://rag.local/entity/Jang_Pung> <http://www.w3.org/2000/01/rdf-schema#label> "장풍" .',
    '<http://rag.local/entity/Oh_Il_Nam> <http://rag.local/relation/taught_to> <http://rag.local/entity/Sung_Ki_Hoon> .',
    '<http://rag.local/entity/Oh_Il_Nam> <http://www.w3.org/2000/01/rdf-schema#label> "오일남" .',
    '<http://rag.local/entity/Sung_Ki_Hoon> <http://rag.local/relation/received> <http://rag.local/entity/Jang_Pung> .',
    '<http://rag.local/entity/Sung_Ki_Hoon> <http://www.w3.org/2000/01/rdf-schema#label> "성기훈" .'
]

def test_insertion():
    print("--- Testing Fuseki Insertion ---")
    print(f"Target KB: {KB_ID}")
    
    success = fuseki_client.insert_triples(KB_ID, TRIPLES)
    
    if success:
        print("✅ Insertion successful!")
        
        # Verify
        query = """
        SELECT ?s ?p ?o WHERE {
            <http://rag.local/entity/Duke> ?p ?o .
        }
        """
        results = fuseki_client.query_sparql(KB_ID, query)
        count = len(results.get("results", {}).get("bindings", []))
        print(f"Verified: Found {count} triples for Duke_Test")
    else:
        print("❌ Insertion failed.")

if __name__ == "__main__":
    test_insertion()
