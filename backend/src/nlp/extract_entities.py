def get_entities(doc):
    """
    Extracts named entities and concepts from a spaCy document.
    
    Args:
        doc: A processed spaCy Doc object.
        
    Returns:
        list[dict]: A list of extracted entities with their labels.
    """
    entities = []
    
    # Target technical entity labels often found in patents
    # ORG (Organizations), PRODUCT (Products/Technologies), GPE (Locations)
    target_labels = {'ORG', 'PRODUCT', 'GPE', 'PERSON', 'FAC'}
    
    for ent in doc.ents:
        if ent.label_ in target_labels:
            # We want unique objects, deduplication can be handled downstream 
            entities.append({
                "text": ent.text,
                "label": ent.label_
            })
            
    # Remove strict duplicates if any exist in the exact same format
    unique_entities = [dict(t) for t in {tuple(d.items()) for d in entities}]
    return unique_entities
