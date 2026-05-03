from typing import Dict, Any

def validate_llm_output(output: Dict[str, Any]) -> bool:
    """
    Validates structural integrity of the LLM output and filters invalid keywords in place.
    Returns False ONLY if the structure is broken or 0 valid keywords remain.
    """
    # 1. Maintain Strict JSON Structure
    if not isinstance(output, dict):
        return False
        
    required_keys = {"clean_text", "keywords", "entities"}
    if not required_keys.issubset(output.keys()):
        return False
        
    if not isinstance(output.get("clean_text"), str):
        return False
        
    raw_keywords = output.get("keywords")
    if not isinstance(raw_keywords, list):
        return False
        
    if not isinstance(output.get("entities"), list):
        return False
        
    # 2. Relaxed Keyword Filtering Strategy
    generic_words = {"system", "method", "process", "device", "apparatus", "data", "technique"}
    valid_keywords = []
    
    for kw in raw_keywords:
        if not isinstance(kw, str):
            continue
            
        kw_clean = kw.strip().lower()
        words = kw_clean.split()
        
        # Must be 2-4 words
        if len(words) < 2 or len(words) > 4:
            continue
            
        # Reject if the phrase is EXCLUSIVELY made of generic words (e.g., "data system")
        # But allow phrases like "intrusion detection system"
        if all(w in generic_words for w in words):
            continue
            
        valid_keywords.append(kw_clean)
        
    # 3. Strengthen Keyword Quality (Keep top 6 most meaningful if too many)
    if len(valid_keywords) > 6:
        valid_keywords = valid_keywords[:6]
        
    # 4. Final Fallback Check
    if not valid_keywords:
        return False
        
    output["keywords"] = valid_keywords
    return True
