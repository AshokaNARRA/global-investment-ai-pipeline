import os
import sqlite3
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load safe environment variables
load_dotenv()

# Configure API Client securely via environment variables
API_KEY = os.environ.get("MACRO_AGENT_API_KEY")
if not API_KEY:
    raise ValueError("Configuration Error: Required agent authentication key missing.")

# Relocated database configuration to abstract paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(base_dir, 'Dashboard_Data', 'analytics_cache.db')

# Standard market vectors used for structured analytical mapping
VALID_VECTORS = [
    "Interest Rates", "Inflation", "Consumer Spending", "Oil & Gas",
    "Technology", "Banking & Finance", "Healthcare", "Real Estate",
    "Supply Chain", "Defense", "Biotechnology"
]

def verify_news_plausibility(headline: str) -> str:
    """
    Evaluates raw inbound unstructured text using risk parameters 
    to filter noise/hallucinations from actionable macro alerts.
    """
    # Core system instructions abstracted to separate structural logic from prompt weights
    prompt = f"""
    Context: Institutional risk filtering and validation pipeline.
    Target Headline: "{headline}"
    
    Task: Classify if the statement matches standard macro reporting frameworks or contains high anomaly parameters.
    Respond strictly with "Verified" or "Pending Consensus" in an unformatted text response.
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if "Verified" in raw_text:
            return "Verified"
        return "Pending Consensus"
    except Exception as e:
        print(f"⚠️ Validation checkpoint bypassed to fallback state: {e}")
        return "Pending Consensus"

def analyze_news(headline: str, source_url: str = "Unknown"):
    """
    Ingests raw macro headlines, orchestrates LLM payload delivery for structured 
    vector scoring, executes verification routing, and commits results to downstream warehouse.
    """
    print(f"\nProcessing Pipeline Ingestion for: '{headline}'")
    
    # Proprietary strategic prompt weightings and specific persona guidelines removed for IP protection
    prompt = f"""
    Context: Structured financial data engineering pipeline.
    Analyze the following event string and derive categorical impact metrics.
    
    Target: "{headline}"
    Approved Schema: {json.dumps(VALID_VECTORS)}
    
    Provide numerical evaluations strictly mapped to the approved array. 
    Output must be clean, valid JSON formatted text without wrappers.
    """
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        raw_text = raw_text.replace('```json', '').replace('```', '').strip()
        vectors_json = json.loads(raw_text)
        print("✓ Structured impact mapping derived successfully.")
        
        # Tiered Verification Logic based on Institutional Ingestion white-lists
        verification_status = "Pending Consensus"
        institutional_feeds = ['wsj.com', 'bloomberg.com', 'finance.yahoo.com', 'reuters.com', 'cnbc.com']
        
        if any(feed in source_url.lower() for feed in institutional_feeds):
            verification_status = "Verified"
            print("✓ Validated against Tier-1 Institutional source list.")
        else:
            print("⏳ Source unrecognized. Initializing heuristic fallback verification...")
            verification_status = verify_news_plausibility(headline)
            print(f" ↳ Automated Verification Verdict: {verification_status}")

        # Transaction execution to relational data tier
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO macro_events (source_url, headline, extracted_vectors_json, verification_status)
            VALUES (?, ?, ?, ?)
        ''', (source_url, headline, json.dumps(vectors_json), verification_status))
        
        conn.commit()
        conn.close()
        print("✓ Ingestion cycle completed. Relational records committed.")
        
    except Exception as e:
        print(f"❌ Processing exception caught within data pipeline: {e}")

if __name__ == "__main__":
    # Local validation sequence demonstrating end-to-end integration
    sample_feed = "Federal Reserve announces unexpected 50 basis point rate hike to combat sticky inflation."
    analyze_news(sample_feed, source_url="https://wsj.com/simulated")