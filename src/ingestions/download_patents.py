import requests
import pandas as pd
import os
import time

# Config
BASE_URL = "https://api.patentsview.org/patents/query"
OUTPUT_FILE = "data/raw/patents_sample.csv"
TOPIC = "medecine"  # Change this to your interest

def fetch_patents(query_text, max_results=1000):
    print(f"Searching for patents related to: '{query_text}'...")
    
    # Define the query JSON (PatentsView syntax)
    # We want patents where the title or abstract contains the keyword
    query = {
        "_or": [
            {"_text_any": {"patent_title": query_text}},
            {"_text_any": {"patent_abstract": query_text}}
        ]
    }
    
    # Define fields we want to get back
    fields = [
        "patent_number", "patent_title", "patent_abstract", "patent_date",
        "inventor_first_name", "inventor_last_name",
        "assignee_organization"
    ]
    
    all_patents = []
    per_page = 50  # API limit per request
    
    for page in range(1, (max_results // per_page) + 2):
        params = {
            "q": str(query),
            "f": str(fields),
            "o": {"page": page, "per_page": per_page}
        }
        
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            data = response.json()
            
            if "patents" not in data:
                print("No more data found.")
                break
                
            batch = data['patents']
            all_patents.extend(batch)
            print(f"   Fetched page {page} ({len(batch)} patents)...")
            
            if len(all_patents) >= max_results:
                break
                
            # Be nice to the API
            time.sleep(1)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    # Save to CSV
    if all_patents:
        df = pd.DataFrame(all_patents)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Downloaded {len(df)} patents to {OUTPUT_FILE}")
    else:
        print("No patents found.")

if __name__ == "__main__":
    fetch_patents(TOPIC)