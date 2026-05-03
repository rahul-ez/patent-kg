import re
from collections import Counter

def _convert_verb_noun(chunk):
    """
    Rule-based converter for "VERB + ..." -> "... + Noun-form"
    e.g. "detecting road potholes" -> "road pothole detection", "monitoring traffic conditions" -> "traffic condition monitoring"
    """
    verb_to_noun = {
        "detecting": "detection",
        "analyzing": "analysis",
        "generating": "generation",
        "evaluating": "evaluation",
        "producing": "production",
        "creating": "creation",
        "improving": "improvement",
        "processing": "processing",
        "monitoring": "monitoring"
    }
    
    if len(chunk) >= 2 and chunk[0].text.endswith("ing") and any(t.pos_ == "NOUN" for t in chunk):
        verb_text = chunk[0].text.lower()
        noun_form = verb_to_noun.get(verb_text, verb_text) 
        
        rest_of_phrase = []
        for t in chunk[1:]:
            if t.pos_ == "DET":
                continue
            if t.pos_ in ["NOUN", "PROPN"]:
                rest_of_phrase.append(t.lemma_.lower())
            else:
                rest_of_phrase.append(t.text.lower())
                
        if rest_of_phrase:
            return " ".join(rest_of_phrase) + " " + noun_form
            
    return None

def get_keywords(doc, entities, top_n=5):
    """
    Extracts high-value technical concepts, prioritizing long technical noun phrases and explicitly 
    avoiding generic words, vague adjectives, and named entities. Normalizes to base lemmas.
    """
    keywords = []
    entity_texts = {re.sub(r'[^a-z0-9]', '', e["text"].lower()) for e in entities}
    
    generic_words = {"method", "system", "device", "apparatus", "process", "means", "use", "invention", "present", "data", "technique", "computing"}
    vague_adj = {"novel", "advanced", "efficient", "improved", "different", "plurality", "various"}
    weak_trailing = r'\s+(algorithm|model|approach|technique)$'
    
    for chunk in doc.noun_chunks:
        # Require at least one strict NOUN in the chunk
        if not any(t.pos_ == "NOUN" for t in chunk):
            continue
            
        # 1. Use simple rule-based Verb->Noun restructuring ("detecting road potholes" -> "road pothole detection")
        converted = _convert_verb_noun(chunk)
        if converted:
            text = converted
        else:
            # Build normalized phrase (lemmatizing nouns, removing vague adjectives & determiners)
            normalized_tokens = []
            starts_with_verb = False
            
            for i, t in enumerate(chunk):
                t_text = t.text.lower()
                
                # Must NOT start with a verb (unless restructuring caught it)
                if i == 0 and t.pos_ == "VERB":
                    starts_with_verb = True
                    break
                    
                if t.pos_ == "DET" or t_text in vague_adj:
                    continue
                if t.pos_ == "NOUN":
                    normalized_tokens.append(t.lemma_.lower())
                else:
                    normalized_tokens.append(t_text)
                    
            if starts_with_verb or not normalized_tokens:
                continue
                
            text = " ".join(normalized_tokens).strip()
            
        # 2. Clean leading conjunctions/prepositions and weak trailing words
        text = re.sub(r'^(and|or|with)\s+', '', text).strip()
        text = re.sub(weak_trailing, '', text).strip()
        
        # Rule 3: Limit Phrase Length (STRICTLY Min 2 words, Max 4 words)
        word_count = len(text.split())
        if word_count < 2 or word_count > 4:
            continue
            
        # Ensure noun chunk is viable and technical
        if not text or text in generic_words:
            continue
            
        # Prevent any overlap with extracted named entities
        clean_text_alpha = re.sub(r'[^a-z0-9]', '', text)
        if any(ent in clean_text_alpha or clean_text_alpha in ent for ent in entity_texts):
            continue
            
        keywords.append(text)
                    
    # Frequency for tie-breaking
    freq = Counter(keywords)
    
    # Rule 4: Handle Redundant Phrases
    unique_candidates = set(keywords)
    final_keywords = set()
    
    # Sort candidates by length descending to process longest, most informative phrases first
    sorted_unique = sorted(unique_candidates, key=lambda k: len(k.split()), reverse=True)
    
    for kw in sorted_unique:
        # If the phrase is fully contained in a more informative final keyword, drop it
        if not any(kw in fkw for fkw in final_keywords):
            final_keywords.add(kw)
            
    # Sort strictly by phrase length first, then frequency
    def scoring_logic(kw):
        return (len(kw.split()), freq[kw])
        
    ranked_keywords = sorted(list(final_keywords), key=scoring_logic, reverse=True)
    return ranked_keywords[:top_n]
