from datasets import load_dataset
import pandas as pd
import os

# Config
OUTPUT_FILE = "data/raw/patents_sample.csv"
SAMPLE_SIZE = 1000  # How many patents you want
YEAR = "2016"       # We pick a specific year to make the download fast

def fetch_huggingface_patents():
    print(f"🚀 Downloading patents from Hugging Face (Harvard USPTO Dataset)...")
    
    # Load a specific subset (e.g., Utility patents from 2016)
    # "streaming=True" lets us download just a few without downloading 500GB
    try:
        dataset = load_dataset(
            "HUPD/hupd", 
            name="sample", 
            split="train", 
            streaming=True,
            trust_remote_code=True
        )
        
        patents_list = []
        print(f"⏳ Fetching first {SAMPLE_SIZE} patents...")

        # Iterator to get the first N records
        for i, record in enumerate(dataset):
            if i >= SAMPLE_SIZE:
                break
            
            # Extract only what we need
            patents_list.append({
                "patent_number": record.get("patent_number"),
                "patent_title": record.get("title"),
                "patent_abstract": record.get("abstract"),
                "patent_date": record.get("filing_date"),
                "ipc_code": record.get("main_ipc_label")  # Helpful for classification
            })
            
            if (i + 1) % 100 == 0:
                print(f"   ... grabbed {i + 1} patents")

        # Save to CSV
        df = pd.DataFrame(patents_list)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Success! Saved {len(df)} patents to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_huggingface_patents()