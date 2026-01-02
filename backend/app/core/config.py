from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Management System"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_system.db"
    
    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: str = "19530"

    # Fuseki
    FUSEKI_URL: str = "http://localhost:3030"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
