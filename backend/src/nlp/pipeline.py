import json
import spacy
from typing import Dict, Any

# Local module imports
from .preprocess import clean_text, light_preprocess, post_process_llm
from .extract_entities import get_entities
from .keywords import get_keywords
from .llm_processor import call_llm_processor
from .validator import validate_llm_output

# Initialize spaCy model safely
print("Loading NLP Model (en_core_web_sm)...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    print("Model not found. Downloading via Python...")
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

def run_hybrid_pipeline(text_id: str, raw_text: str) -> Dict[str, Any]:
    """
    Hybrid NLP pipeline executing LLM first -> Validation -> Post-Processing.
    Falls back to robust spaCy pipeline if LLM fails or is unavailable.
    """
    # Step 1: Light Preprocess
    prepped_text = light_preprocess(raw_text)
    
    # Step 2: LLM Processing
    llm_output = call_llm_processor(prepped_text)
    
    # Step 3: Output Validation
    if llm_output and validate_llm_output(llm_output):
        # Step 4: Post-Processing
        final_output = post_process_llm(llm_output)
        
        # Ensure Core Concept Coverage (3-6 keywords minimum)
        if len(final_output["keywords"]) < 3:
            doc = nlp(final_output["clean_text"])
            extra_keywords = get_keywords(doc, final_output["entities"], top_n=6)
            for kw in extra_keywords:
                if not any(kw in fkw for fkw in final_output["keywords"]):
                    final_output["keywords"].append(kw)
                    if len(final_output["keywords"]) >= 6:
                        break
                        
        final_output["patent_id"] = text_id
        return final_output
        
    # Step 5: Fallback to existing spaCy pipeline
    print("LLM processing unavailable or failed validation. Utilizing spaCy fallback...")
    
    cleaned_txt = clean_text(raw_text)
    doc = nlp(cleaned_txt)
    
    entities = get_entities(doc)
    keywords = get_keywords(doc, entities, top_n=5)
    
    return {
        "patent_id": text_id,
        "clean_text": cleaned_txt,
        "keywords": keywords,
        "entities": entities
    }

def process_patent(patent_id: str, title: str, abstract: str) -> Dict[str, Any]:
    """
    Full pipeline to convert a raw patent into structured JSON formats.
    """
    raw_text = f"{title}. {abstract}"
    return run_hybrid_pipeline(str(patent_id), raw_text)

def process_user_query(query_text: str) -> Dict[str, Any]:
    """
    Applies the exact same hybrid NLP pipeline to real-time user input/queries.
    """
    return run_hybrid_pipeline("user_query", query_text)

def prepare_embedding_input(processed_data: Dict[str, Any]) -> str:
    """
    Prepares a single consistent string ready for an embedding model, combining the text and top keywords naturally.
    """
    clean_txt = processed_data.get("clean_text", "").strip()
    kwds = processed_data.get("keywords", [])
    
    # Naturally fuse the text rather than using dense array brackets
    if kwds:
        embedding_str = f"{clean_txt}. Key technical concepts: {', '.join(kwds)}."
    else:
        embedding_str = clean_txt
        
    return embedding_str

if __name__ == "__main__":
    # --- TESTING BLOCK ---
    print("\n--- TEST: PATENT PROCESSING ---")
    sample_title = "Machine Learning Method for Autonomous Drone Navigation"
    sample_abstract = "This invention provides a system utilizing neural networks and LiDAR sensors. Apple Inc. developed this novel architecture in California to improve pathfinding in urban environments."
    
    patent_json = process_patent("PAT-101", sample_title, sample_abstract)
    print(json.dumps(patent_json, indent=2))
    
    print("\nEmbedding String Format:")
    print(prepare_embedding_input(patent_json))
    
    print("\n--- TEST: USER QUERY PROCESSING ---")
    query = "Show me patents related to federated learning and drone cameras by Apple."
    query_json = process_user_query(query)
    print(json.dumps(query_json, indent=2))
