import pandas as pd
import spacy
import os
from tqdm import tqdm

# Configuration
INPUT_FILE = "../data/processed/patents.csv"
OUTPUT_DIR = "../data/processed"

def extract_entities():
    print("Loading NLP Model (en_core_web_sm)...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        import subprocess
        print("Model not found. Downloading via Python...")
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")

    print(f"Loading data from {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run normalize_data.py first.")
        return

    entities_list = []
    keywords_list = []

    print("Extracting entities from abstracts...")
    # Limit to 1000 for local test/timeout, can process all in batch later
    for idx, row in tqdm(df.head(1000).iterrows(), total=min(1000, len(df))):
        pid = row['patent_id']
        abstract = str(row['abstract'])
        
        if abstract == "nan" or not abstract:
            continue
            
        doc = nlp(abstract)
        
        # Extract Entities (ORG, PERSON, GPE, PRODUCT)
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'PERSON']:
                entities_list.append({
                    "patent_id": pid,
                    "entity_text": ent.text,
                    "label": ent.label_,
                    "confidence_score": 0.95 # Mocking confidence score requirement
                })
        
        # Extract Keywords (Nouns/Chunks)
        for chunk in doc.noun_chunks:
            # Filter stop words and short terms
            if len(chunk.text) > 3 and not chunk.root.is_stop:
                keywords_list.append({
                    "patent_id": pid,
                    "keyword": chunk.text.lower()
                })

    # Save Entities
    print("Saving entities.csv...")
    ent_df = pd.DataFrame(entities_list)
    ent_df.drop_duplicates(inplace=True)
    ent_df.to_csv(os.path.join(OUTPUT_DIR, "entities.csv"), index=False)

    # Save Keywords
    print("Saving keywords.csv...")
    kwd_df = pd.DataFrame(keywords_list)
    kwd_df.drop_duplicates(inplace=True)
    kwd_df.to_csv(os.path.join(OUTPUT_DIR, "keywords.csv"), index=False)
    
    print("Extraction complete!")

if __name__ == "__main__":
    extract_entities()
