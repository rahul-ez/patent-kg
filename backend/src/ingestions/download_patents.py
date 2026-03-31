from dotenv import load_dotenv
import requests
import pandas as pd
import os
import time
import json
load_dotenv()
# ==========================================
# CONFIGURATION
# ==========================================
API_KEY = os.getenv("PATENTSVIEW_API_KEY")
BASE_URL = "https://search.patentsview.org/api/v1/patent/"
OUTPUT_FILE = "../data/raw/patents_sample.csv"
QUERY_TOPIC = "Artificial Intelligence" # Change to your topic
MAX_RESULTS = 100000 # Start with 100k patents (first pass)

# ==========================================
# MAIN SCRIPT
# ==========================================
def fetch_live_patents():
    print(f" Connecting to PatentsView Live API...")
    print(f"Topic: {QUERY_TOPIC}")

    # 1. Define Query (Elasticsearch Syntax)
    # We want patents where the title or abstract contains the topic
    # AND the patent date is recent (e.g., after 2020)
    query = {
        "_and": [
            {"_gte": {"patent_date": "2020-01-01"}},
            {"_or": [
                {"_text_any": {"patent_title": QUERY_TOPIC}},
                {"_text_any": {"patent_abstract": QUERY_TOPIC}}
            ]}
        ]
    }

    fields = [
        "patent_id",                # Changed from patent_number
        "patent_title",
        "patent_abstract",
        "patent_date",
        "inventors.inventor_last_name",  # Changed structure
        "inventors.inventor_first_name",
        "assignees.assignee_organization"
    ]

    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }

    all_patents = []
    results_per_page = 50
    page = 1

    # 3. Pagination Loop
    while len(all_patents) < MAX_RESULTS:
        payload = {
            "q": query,
            "f": fields,
            "o": {"page": page, "per_page": results_per_page}
        }

        try:
            response = requests.post(BASE_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code} - {response.text}")
                break

            data = response.json()
            batch = data.get("patents", [])

            if not batch:
                print("No more data found.")
                break

            # 4. Flatten Data
            for p in batch:
                # Flatten Inventors
                inventors = []
                if "inventors" in p and p["inventors"]:
                    for inv in p["inventors"]:
                        first = inv.get("inventor_name_first", "") # Update key
                        last = inv.get("inventor_name_last", "")   # Update key
                        inventors.append(f"{first} {last}".strip())
                
                # Flatten Assignees
                assignees = []
                if "assignees" in p and p["assignees"]:
                    for ass in p["assignees"]:
                        org = ass.get("assignee_organization", "")
                        if org:
                            assignees.append(org)

                # Clean Record
                clean_record = {
                    "patent_number": p.get("patent_id"), # Update key here too!
                    "title": p.get("patent_title"),
                    "abstract": p.get("patent_abstract"),
                    "date": p.get("patent_date"),
                    "inventors": "; ".join(inventors),
                    "assignees": "; ".join(assignees)
                }
                all_patents.append(clean_record)

            print(f"   Page {page}: Fetched {len(batch)} patents (Total: {len(all_patents)})")
            page += 1
            
            # Be nice to the API (Rate limit is 45 req/min)
            time.sleep(1.5)

        except Exception as e:
            print(f"Script Error: {e}")
            break

    # 5. Save to CSV
    if all_patents:
        df = pd.DataFrame(all_patents)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Saved {len(df)} patents to {OUTPUT_FILE}")
    else:
        print("No patents downloaded.")

if __name__ == "__main__":
    fetch_live_patents()