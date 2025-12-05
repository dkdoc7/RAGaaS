from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from typing import List, Dict

class ChunkingService:
    def __init__(self):
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def chunk_by_size(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )
        return splitter.split_text(text)

    def chunk_parent_child(self, text: str, parent_size: int = 2000, child_size: int = 500) -> List[Dict]:
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=parent_size, chunk_overlap=0)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=child_size, chunk_overlap=100)
        
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

    def chunk_context_aware(self, text: str) -> List[str]:
        # Simple markdown splitter for now
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        docs = markdown_splitter.split_text(text)
        return [doc.page_content for doc in docs]

chunking_service = ChunkingService()
