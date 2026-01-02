from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict
from app.core.config import settings

class ChunkingService:
    def __init__(self):
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def chunk_by_size(self, text: str, chunk_size: int = 1000, overlap: int = 200, separators: List[str] = None) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=separators or ["\n\n", "\n", " ", ""]
        )
        return splitter.split_text(text)

    def chunk_parent_child(self, text: str, parent_size: int = 2000, child_size: int = 500, parent_overlap: int = 0, child_overlap: int = 100, separators: List[str] = None) -> List[Dict]:
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size, 
            chunk_overlap=parent_overlap,
            separators=separators or ["\n\n", "\n", " ", ""]
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size, 
            chunk_overlap=child_overlap,
            separators=separators or ["\n\n", "\n", " ", ""]
        )
        
        parents = parent_splitter.split_text(text)
        chunks = []
        
        for i, parent_text in enumerate(parents):
            children = child_splitter.split_text(parent_text)
            for child_text in children:
                chunks.append({
                    "content": child_text,
                    "metadata": {
                        "parent_id": i,
                        "parent_content": parent_text
                    }
                })
        return chunks

    def chunk_context_aware(self, text: str, headers_to_split_on: List[tuple] = None) -> List[str]:
        # Default headers if none provided
        if not headers_to_split_on:
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        docs = markdown_splitter.split_text(text)
        return [doc.page_content for doc in docs]

    def chunk_semantic(self, text: str, buffer_size: int = 1, breakpoint_threshold_type: str = "percentile", breakpoint_threshold_amount: float = 95.0) -> List[str]:
        embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        semantic_splitter = SemanticChunker(
            embeddings,
            buffer_size=buffer_size,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount
        )
        docs = semantic_splitter.create_documents([text])
        return [doc.page_content for doc in docs]

    def split_into_sections(self, text: str, section_size: int = 6000, overlap: int = 500) -> List[str]:
        """
        Split text into larger sections for graph extraction.
        These sections provide broader context for entity/relation extraction.
        
        Args:
            section_size: Size of each section in characters (default: 6000, ~1500 tokens)
            overlap: Overlap between sections to preserve cross-boundary context
        
        Returns:
            List of section texts
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=section_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return splitter.split_text(text)

chunking_service = ChunkingService()
