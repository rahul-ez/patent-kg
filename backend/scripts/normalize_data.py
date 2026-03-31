import pandas as pd
import os
import uuid

# Configuration
INPUT_FILE = "../data/raw/patents_sample.csv"
OUTPUT_DIR = "../data/processed"

def normalize_data():
    print(f"Loading raw data from {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Please run download_patents.py first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Patents Table
    # Schema: patent_id, title, abstract, date, ipc_codes, claims_text
    print("Generating patents.csv...")
    patents_df = df[['patent_number', 'title', 'abstract', 'date']].copy()
    patents_df.rename(columns={'patent_number': 'patent_id'}, inplace=True)
    # Mocking ipc_codes and claims_text as they aren't fully present in the basic sample API fetch
    patents_df['ipc_codes'] = "G06N" 
    patents_df['claims_text'] = ""
    patents_df.to_csv(os.path.join(OUTPUT_DIR, "patents.csv"), index=False)

    # 2. Inventors Table
    # Schema: patent_id, inventor_name, inventor_id
    print("Generating inventors.csv...")
    inventors_list = []
    for idx, row in df.iterrows():
        pid = row['patent_number']
        invs = str(row['inventors']).split(";")
        for inv in invs:
            inv = inv.strip()
            if inv and inv != "nan":
                # Generate a mock unique ID for the inventor
                inventors_list.append({
                    "patent_id": pid,
                    "inventor_name": inv,
                    "inventor_id": f"INV-{abs(hash(inv))}"
                })
    inventors_df = pd.DataFrame(inventors_list)
    inventors_df.to_csv(os.path.join(OUTPUT_DIR, "inventors.csv"), index=False)

    # 3. Assignees Table
    # Schema: patent_id, company_name, company_id (if available)
    print("Generating assignees.csv...")
    assignees_list = []
    for idx, row in df.iterrows():
        pid = row['patent_number']
        orgs = str(row['assignees']).split(";")
        for org in orgs:
            org = org.strip()
            if org and org != "nan":
                assignees_list.append({
                    "patent_id": pid,
                    "company_name": org,
                    "company_id": f"ORG-{abs(hash(org))}"
                })
    assignees_df = pd.DataFrame(assignees_list)
    assignees_df.to_csv(os.path.join(OUTPUT_DIR, "assignees.csv"), index=False)

    # 4. Citations Table
    # Schema: citing_id, cited_id
    # Without API citation depth, we'll create an empty template or random sample for schema validation
    print("Generating citations.csv...")
    citations_df = pd.DataFrame(columns=['citing_id', 'cited_id'])
    citations_df.to_csv(os.path.join(OUTPUT_DIR, "citations.csv"), index=False)

    print("Normalization complete! All files saved to data/processed/")

if __name__ == "__main__":
    normalize_data()
