
import asyncio
import sys
import os
import numpy as np

# Add app to path
sys.path.append(os.getcwd())

from app.services.embedding import embedding_service

async def main():
    query = "오영수 배우의 역할은?"
    # Sample chunk content that should be relevant
    chunk_content = "오영수 - 오일남 역: 1번 참가자. 뇌종양에 걸린 칠순 노인으로 치매 증상이 있다."
    
    print(f"Query: {query}")
    print(f"Chunk: {chunk_content}")
    
    try:
        # 1. Embed
        embeddings = await embedding_service.get_embeddings([query, chunk_content])
        q_vec = np.array(embeddings[0])
        d_vec = np.array(embeddings[1])
        
        # 2. Compute Cosine
        norm1 = np.linalg.norm(q_vec)
        norm2 = np.linalg.norm(d_vec)
        cosine = np.dot(q_vec, d_vec) / (norm1 * norm2)
        print(f"Cosine Similarity: {cosine:.4f}")
        
        # 3. Compute L2
        l2_dist = np.linalg.norm(q_vec - d_vec)
        print(f"L2 Distance: {l2_dist:.4f}")
        
        # 4. Computed Sim Score
        sim_score = 1.0 / (1.0 + l2_dist)
        print(f"Converted Sim Score: {sim_score:.4f}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
