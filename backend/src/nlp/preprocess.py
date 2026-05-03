import re

def clean_text(text: str) -> str:
    """
    Cleans raw text by lowercasing, removing special characters, and stripping extra spaces.
    
    Args:
        text (str): The raw text to clean.
        
    Returns:
        str: Cleaned text.
    """
    if not text or not isinstance(text, str):
        return ""
        
    text = text.lower()
    
    # 0. Fix awkward sentence starts involving "a/an" followed by gerunds
    text = re.sub(r'\b(a|an)\s+(\w+ing)\b', r'\2', text)
    text = re.sub(r'^(a|an)\s+', '', text)
    
    # 1. Regex-based removal of boilerplate phrases (e.g., "method for", "system for")
    text = re.sub(r'\b(method(s)?|system(s)?|device(s)?|apparatus(es)?|process(es)?)\s+(for|of)\b', ' ', text)
    
    # Removes other common patent intro boilerplate
    boilerplate = [
        "the present invention", "this invention", "the invention",
        "provides a", "relates to", "disclosed is", "described herein"
    ]
    for phrase in boilerplate:
        text = text.replace(phrase, " ")
        
    # 2. Extract specific technical characters (alphanumeric and spacing/dashes)
    text = re.sub(r'[^a-z0-9\s.,-]', ' ', text)
    
    # 3. Clean up loose spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def light_preprocess(text: str) -> str:
    """
    Step 1: Light rule-based prep before hitting the LLM.
    Removes extra spaces and strange characters without breaking meaning.
    """
    if not text or not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s.,-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def post_process_llm(output: dict) -> dict:
    """
    Step 4: Rule-based post-processing.
    Normalizes lowercase, strips whitespace, handles redundancy, and sorts by importance.
    """
    output["clean_text"] = output.get("clean_text", "").strip().lower()
    
    raw_kw = output.get("keywords", [])
    
    # Sort descending by length so we process longest (most informative) phrases first
    sorted_kw = sorted(raw_kw, key=lambda k: len(str(k).split()), reverse=True)
    
    cleaned_kw = []
    for k in sorted_kw:
        k_clean = str(k).strip().lower()
        if not k_clean:
            continue
            
        # Redundancy check: If it's already contained in an accepted longer keyword, skip it
        if not any(k_clean in accepted for accepted in cleaned_kw):
            cleaned_kw.append(k_clean)
            
    # Enforce keyword limits (keep up to 6)
    output["keywords"] = cleaned_kw[:6]
    
    raw_ent = output.get("entities", [])
    seen_e = set()
    cleaned_ent = []
    for e in raw_ent:
        e_clean = str(e).strip().lower()
        if e_clean and e_clean not in seen_e:
            seen_e.add(e_clean)
            cleaned_ent.append(e_clean)
            
    output["entities"] = cleaned_ent
    return output
