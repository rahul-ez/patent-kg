import os
import time
import json
import requests
import pandas as pd
from tqdm import tqdm

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = "https://api.patentsview.org/patents/query"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "raw", "patents_sample.csv")

# Domain sampling definitions
DOMAINS = {
    "AI_Software": {
        "cpc": ["G06F", "G06N"],
        "keywords": ["artificial intelligence", "machine learning", "neural network", "deep learning", "software", "computing", "algorithm"],
        "target": 10000
    },
    "Medical_Biomedical": {
        "cpc": ["A61"],
        "keywords": ["medical device", "surgical", "pharmaceutical", "healthcare", "biomedical", "implant", "therapy"],
        "target": 8000
    },
    "Electronics_IoT": {
        "cpc": ["H01", "H02"],
        "keywords": ["internet of things", "sensor", "wireless", "semiconductor", "circuit", "processor", "transistor", "antenna"],
        "target": 8000
    },
    "Mechanical_Engineering": {
        "cpc": ["F16", "B23"],
        "keywords": ["mechanical", "hydraulic", "manufacturing", "machine tool", "engine", "valve", "turbine"],
        "target": 8000
    },
    "Automotive_Mobility": {
        "cpc": ["B60"],
        "keywords": ["automotive", "vehicle", "mobility", "car", "transportation", "powertrain", "chassis"],
        "target": 5000
    },
    "Energy_Materials": {
        "cpc": ["Y02", "C", "B01"],
        "keywords": ["energy", "battery", "solar", "wind turbine", "smart grid", "materials", "chemical", "polymer"],
        "target": 10000
    }
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_existing_ids(filepath):
    """Load existing patent IDs to prevent duplicates."""
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, usecols=['patent_id'])
            return set(df['patent_id'].dropna().astype(str).tolist())
        except Exception as e:
            print(f"Could not load existing IDs (or file is empty): {e}")
    return set()

def build_query(keyword_batch):
    """Construct a simplified query JSON object using keyword batch."""
    keywords_str = " ".join(keyword_batch)
    query = {
        "_and": [
            {"_gte": {"patent_date": "2015-01-01"}},
            {
                "_text_any": {
                    "patent_title": keywords_str
                }
            }
        ]
    }
    return query

def process_results(batch, domain_name, seen_ids):
    """Extract, clean, and deduplicate patent data from a batch."""
    processed = []
    for p in batch:
        # Patent ID handling (fallback to patent_number if needed)
        pid = p.get("patent_id") or p.get("patent_number")
        if not pid or str(pid) in seen_ids:
            continue
            
        title = str(p.get("patent_title", "")).strip()
        abstract = str(p.get("patent_abstract", "")).strip()
        date = str(p.get("patent_date", "")).strip()
        
        if len(abstract) < 50:
            continue
            
        # Flatten Arrays
        inventors = [f"{inv.get('inventor_name_first', '')} {inv.get('inventor_name_last', '')}".strip() 
                     for inv in p.get("inventors", []) if isinstance(inv, dict)]
        assignees = [ass.get("assignee_organization", "").strip() 
                     for ass in p.get("assignees", []) if isinstance(ass, dict) and ass.get("assignee_organization")]
        
        # Add to processed records
        processed.append({
            "patent_id": str(pid),
            "patent_title": title,
            "patent_abstract": abstract,
            "patent_date": date,
            "inventors": "; ".join(filter(None, inventors)),
            "assignees": "; ".join(filter(None, assignees)),
            "domain": domain_name
        })
        seen_ids.add(str(pid))
        
    return pd.DataFrame(processed)

def fetch_patents(domain_name, domain_info, target_count, seen_ids, output_file):
    """Iteratively fetch patents for a domain and append to CSV."""
    fields = [
        "patent_id",
        "patent_number",
        "patent_title",
        "patent_abstract",
        "patent_date",
        "inventors.inventor_name_last",
        "inventors.inventor_name_first",
        "assignees.assignee_organization",
        "cpc_current.cpc_subgroup_id"
    ]
    
    keywords = domain_info.get("keywords", [])
    # Keyword batching: Use 2-3 keywords per query
    batch_size = 2
    keyword_batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
    
    added_this_domain = 0
    pbar = tqdm(total=target_count, desc=domain_name)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    for kw_batch in keyword_batches:
        if added_this_domain >= target_count:
            break
            
        query = build_query(kw_batch)
        page = 1
        results_per_page = 100
        max_retries = 3
        
        while added_this_domain < target_count:
            payload = {
                "q": query,
                "f": fields,
                "o": {"page": page, "per_page": results_per_page}
            }
            
            success = False
            retries = 0
            batch = []
            
            # ADD DEBUG LOGGING (Before Request)
            print(f"\n[DEBUG] Request Payload for {domain_name} (Batch: {kw_batch}):")
            print(json.dumps(payload, indent=2))
            
            while retries < max_retries and not success:
                try:
                    response = requests.post(BASE_URL, json=payload, headers=headers, timeout=20)
                    
                    # ADD DEBUG LOGGING (After Response)
                    print("\n[DEBUG] Response text preview (first 300 chars):")
                    print(response.text[:300])
                    
                    # ADD RESPONSE VALIDATION
                    if "application/json" not in response.headers.get("Content-Type", ""):
                        print(f"\n[ERROR] Non-JSON response received. Content-Type: {response.headers.get('Content-Type')}")
                        retries += 1
                        time.sleep(2)
                        continue
                        
                    if response.status_code == 200:
                        success = True
                        try:
                            data = response.json()
                            batch = data.get("patents", [])
                        except json.JSONDecodeError:
                            print(f"\n[Warning] Invalid JSON received. Retrying...")
                            retries += 1
                            time.sleep(2)
                    elif response.status_code == 429:
                        time.sleep(5)
                        retries += 1
                    else:
                        print(f"\n[API Error] Status {response.status_code}. Retrying...")
                        retries += 1
                        time.sleep(2)
                except Exception as e:
                    print(f"\n[Connection Error] {e}. Retrying...")
                    retries += 1
                    time.sleep(2)
                    
            if not success:
                print(f"\nMax retries reached for batch {kw_batch} on page {page}. Moving to next batch.")
                break
                
            if not batch:
                print(f"\nNo more data available for batch {kw_batch}.")
                break
                
            df_batch = process_results(batch, domain_name, seen_ids)
            
            if not df_batch.empty:
                # Prevent overfilling if the batch pushes us past target
                if added_this_domain + len(df_batch) > target_count:
                    df_batch = df_batch.head(target_count - added_this_domain)
                    
                added_this_domain += len(df_batch)
                pbar.update(len(df_batch))
                
                # Incremental save (Append mode)
                write_header = not os.path.exists(output_file)
                df_batch.to_csv(output_file, mode='a', header=write_header, index=False)
                
            if added_this_domain >= target_count:
                break
                
            page += 1
            time.sleep(1)
            
    pbar.close()
    return added_this_domain

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("Initializing API data ingestion...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    seen_ids = get_existing_ids(OUTPUT_FILE)
    print(f"Loaded {len(seen_ids)} existing patents to prevent duplication.")
    
    total_added = 0
    
    for domain, info in DOMAINS.items():
        print(f"\n--- Processing Domain: {domain} ---")
        added = fetch_patents(
            domain_name=domain,
            domain_info=info,
            target_count=info["target"],
            seen_ids=seen_ids,
            output_file=OUTPUT_FILE
        )
        total_added += added
        
    print(f"\nIngestion Complete. Added {total_added} new patents in this run.")
    print(f"Results saved progressively to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()