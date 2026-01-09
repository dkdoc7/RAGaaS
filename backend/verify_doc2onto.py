
import os
import sys

# Add app to path
app_dir = os.path.join(os.getcwd(), 'app')
if app_dir not in sys.path:
    sys.path.append(app_dir)

# Mock settings
class MockSettings:
    DOC2ONTO_CONFIG_PATH = "/Users/dukekimm/Works/RAGaaS/backend/doc2onto_config.yml"
    OPENAI_API_KEY = "sk-test"
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"
    FUSEKI_URL = "http://localhost:3030"

# Inject settings
from app.core import config
config.settings = MockSettings()

try:
    from app.services.ingestion.doc2onto import doc2onto_processor
    print(f"Doc2Onto Enabled: {doc2onto_processor.enabled}")
    if doc2onto_processor.client:
        print(f"Config loaded: {doc2onto_processor.client.config.extraction.llm_model}")
        print(f"Extractor type: {type(doc2onto_processor.client._extractor)}")
    else:
        print("Client not initialized")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
