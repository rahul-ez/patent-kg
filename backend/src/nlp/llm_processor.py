import json
import os
from typing import Dict, Any, Optional

# Explicitly load .env file from the project root
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

# Attempt to load and configure the new google-genai client safely
try:
    from google import genai
    from google.genai import types
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        print("Gemini Client successfully initialized!")
    else:
        print("Error: GOOGLE_API_KEY is empty or not found in environment!")
        client = None
except ImportError as e:
    print(f"Error: Failed to import google.genai package. Detailed error: {e}")
    client = None

def call_llm_processor(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Calls the LLM to extract clean text, keywords, and entities.
    Returns the raw JSON dictionary, or None if it fails.
    """
    if not client:
        print("Gemini client not initialized. Missing API key or package.")
        return None
        
    prompt = f"""You are an expert system that extracts structured technical meaning from user ideas.

Convert the following input into a strict JSON format.

INPUT:
"{user_input}"

OUTPUT FORMAT:
{{
  "clean_text": "...",
  "keywords": ["...", "..."],
  "entities": ["...", "..."]
}}

RULES:
- Return ONLY valid JSON (no explanations)
- clean_text:
  - remove filler phrases (e.g., "this invention", "basically")
  - keep meaning intact
  - make it readable
- keywords:
  - 2-6 phrases
  - each 2-4 words
  - must be technical concepts
  - must be noun-based (no verbs)
  - convert verb phrases to noun phrases
  - avoid generic words like "system", "method"
- entities:
  - only real-world names (companies, places, products)
  - optional, can be empty
- all output must be lowercase"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        content = response.text
        
        # Add Debug Logging
        print("\n=== [DEBUG] LLM PROCESSOR ===")
        truncated_response = content[:200] + "..." if len(content) > 200 else content
        print(f"Raw Response (Truncated):\n{truncated_response}")
        
        parsed_json = json.loads(content)
        
        print("\nParsed JSON:")
        print(json.dumps(parsed_json, indent=2))
        print("=============================\n")
        
        return parsed_json
    except Exception as e:
        print(f"LLM Processing failed: {e}")
        return None
