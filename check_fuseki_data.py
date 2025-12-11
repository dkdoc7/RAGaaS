import requests

FUSEKI_URL = "http://localhost:3030"
KB_ID = "171dbd5b-c42d-4cd5-8bb7-ea2044060aed"

# Check if dataset exists
print(f"Checking dataset for {KB_ID}...")
try:
    resp = requests.post(f"{FUSEKI_URL}/$/server", auth=('admin', 'pw123'))
    # Fuseki management logic usually separate, but let's just query
    
    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
    query_url = f"{FUSEKI_URL}/kb_{KB_ID.replace('-', '_')}/query"
    
    print(f"Querying {query_url}...")
    resp = requests.get(query_url, params={'query': query})
    
    if resp.status_code == 200:
        print("Success! Data found:")
        print(resp.json())
    else:
        print(f"Failed: {resp.status_code}")
        print(resp.text)

except Exception as e:
    print(f"Error: {e}")
