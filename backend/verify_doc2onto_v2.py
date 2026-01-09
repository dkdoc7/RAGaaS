
import os
import sys

# Add app to path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.append(app_dir)

from app.core.config import settings
print(f"DOC2ONTO_CONFIG_PATH: '{settings.DOC2ONTO_CONFIG_PATH}'")
print(f"Exists? {os.path.exists(settings.DOC2ONTO_CONFIG_PATH) if settings.DOC2ONTO_CONFIG_PATH else 'N/A'}")

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
