from SPARQLWrapper import SPARQLWrapper, JSON

FUSEKI_URL = "http://localhost:3030"
KB_ID = "09e9662c-e3ed-412c-98b8-dc73dd3a9745"
safe_name = f"kb_{KB_ID.replace('-', '_')}"
DATASET_URL = f"{FUSEKI_URL}/{safe_name}/sparql"

def show_all_triples():
    sparql = SPARQLWrapper(DATASET_URL)
    sparql.setQuery("""
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
            FILTER regex(str(?s), "Duke", "i")
        }
    """)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        print(f"\n--- All Triples in KB {KB_ID} ({len(bindings)}) ---")
        for b in bindings:
            s = b["s"]["value"]
            p = b["p"]["value"]
            o = b["o"]["value"]
            
            # Simple formatting
            s = s.split("/")[-1]
            p = p.split("/")[-1]
            o = o.split("/")[-1]
            
            # Decode
            from urllib.parse import unquote
            s = unquote(s).replace("_", " ")
            p = unquote(p).replace("_", " ")
            o = unquote(o).replace("_", " ")
            
            print(f"{s} --[{p}]--> {o}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    show_all_triples()
