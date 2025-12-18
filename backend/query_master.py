from app.core.fuseki import fuseki_client
import json
import urllib.parse

kb_id = "f60be22f-48b1-4384-98bf-8d836855bfc3"

print("="*70)
print("=== Searching for 오일남 (character name, not actor) ===")
print("="*70 + "\n")

# Find all info about 오일남
oilnam_query = """
PREFIX rel: <http://rag.local/relation/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?sLabel ?predicate ?oLabel
WHERE {
  {
    ?s rdfs:label ?sLabel .
    FILTER regex(?sLabel, "오일남", "i")
    
    ?s ?predicate ?o .
    FILTER (?predicate != rel:hasSource)
    FILTER (?predicate != rdfs:label)
    OPTIONAL { ?o rdfs:label ?oLabel }
  }
  UNION
  {
    ?o rdfs:label ?oLabel .
    FILTER regex(?oLabel, "오일남", "i")
    
    ?s ?predicate ?o .
    FILTER (?predicate != rel:hasSource)
    FILTER (?predicate != rdfs:label)
    OPTIONAL { ?s rdfs:label ?sLabel }
  }
}
"""

print("All relationships involving 오일남:\n")
oilnam_results = fuseki_client.query_sparql(kb_id, oilnam_query)
if oilnam_results and "results" in oilnam_results and "bindings" in oilnam_results["results"]:
    bindings = oilnam_results["results"]["bindings"]
    if bindings:
        for i, b in enumerate(bindings, 1):
            s = b.get("sLabel", {}).get("value", "?")
            o = b.get("oLabel", {}).get("value", b.get("o", {}).get("value", "?"))
            pred = urllib.parse.unquote(b.get("predicate", {}).get("value", "").split("/")[-1])
            print(f"{i}. {s} --[{pred}]--> {o}")
    else:
        print("❌ No entity found for 오일남")
        print("\nLet's check what entities are available that might be related:\n")
        
        # Check entities containing key characters
        related_query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?label
        WHERE {
          ?entity rdfs:label ?label .
          FILTER regex(?label, "(001|일남|기훈|상우|덕수)", "i")
        }
        """
        related_results = fuseki_client.query_sparql(kb_id, related_query)
        for b in related_results.get("results", {}).get("bindings", []):
            print(f"  - {b.get('label', {}).get('value', '')}")

print("\n" + "="*70)
print("=== Checking all entities with 'master' or 'teacher' relationships ===")
print("="*70 + "\n")

master_all_query = """
PREFIX rel: <http://rag.local/relation/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?sLabel ?predicate ?oLabel
WHERE {
  ?s ?predicate ?o .
  
  FILTER regex(str(?predicate), "(master|teacher|스승|제자|student)", "i")
  
  OPTIONAL { ?s rdfs:label ?sLabel }
  OPTIONAL { ?o rdfs:label ?oLabel }
}
"""

print("All master/teacher/student relationships:\n")
master_results = fuseki_client.query_sparql(kb_id, master_all_query)
if master_results and "results" in master_results and "bindings" in master_results["results"]:
    bindings = master_results["results"]["bindings"]
    if bindings:
        for i, b in enumerate(bindings, 1):
            s = b.get("sLabel", {}).get("value", "?")
            o = b.get("oLabel", {}).get("value", "?")
            pred = urllib.parse.unquote(b.get("predicate", {}).get("value", "").split("/")[-1])
            print(f"{i}. {s} --[{pred}]--> {o}")
    else:
        print("❌ No master/teacher relationships found in graph")

print("\n" + "="*70)
print("=== Now let's try with the actual document content ===")
print("="*70 + "\n")

# Let's also check what the document says directly
import requests

search_response = requests.post(
    "http://localhost:8000/api/knowledge-bases/f60be22f-48b1-4384-98bf-8d836855bfc3/retrieve",
    json={
        "query": "성기훈 스승 제자 master teacher 오일남",
        "top_k": 5,
        "strategy": "hybrid",
        "score_threshold": 0.0
    }
)

if search_response.status_code == 200:
    results = search_response.json()
    if results:
        print(f"Found {len(results)} relevant chunks:\n")
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            content = result.get("content", "")
            print(f"Result {i} (Score: {score:.3f}):")
            print(content[:500])
            print("\n" + "-"*70 + "\n")
    else:
        print("No results found in document")

print("\n" + "="*70)
print("=== Checking for '001번' (오일남's player number) ===")
print("="*70 + "\n")

player_001_query = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?label
WHERE {
  ?entity rdfs:label ?label .
  FILTER regex(?label, "001", "i")
}
"""

player_results = fuseki_client.query_sparql(kb_id, player_001_query)
print("Entities with '001':")
for b in player_results.get("results", {}).get("bindings", []):
    print(f"  - {b.get('label', {}).get('value', '')}")
