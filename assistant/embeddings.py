from math import sqrt
import hashlib

def cosine_similarity(vector_a, vector_b):
    if not vector_a or not vector_b:
        return 0.0
    
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same number of dimensions.")
    
    dot_product = sum(
        value_a * value_b
        for value_a, value_b in zip(vector_a, vector_b)
    )
    
    magnitude_a = sqrt(sum(value * value for value in vector_a))
    magnitude_b = sqrt(sum(value * value for value in vector_b))
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)

def create_content_hash(text):
    clean_text = str(text or "").strip()
    
    return hashlib.sha256(
        clean_text.encode("utf-8")
    ).hexdigest()

def rank_embedding_matches(
    query_vector,
    candidates,
    limit=5,
    min_score=0.0,
):
    ranked_matches = []
    
    for candidate in candidates:
        candidate_vector = candidate.get("vector", [])
        
        if not candidate_vector:
            continue
        
        score = cosine_similarity(query_vector, candidate_vector)
        
        if score < min_score:
            continue
        
        match = candidate.copy()
        match["score"] = score
        ranked_matches.append(match)
        
    ranked_matches.sort(
        key=lambda match: match["score"],
        reverse=True
    )
    
    return ranked_matches[:limit]