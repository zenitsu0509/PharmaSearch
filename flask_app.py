import os
import requests # Added for API calls
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from pinecone import Pinecone, ServerlessSpec
# Removed: from sentence_transformers import SentenceTransformer

# --- Basic Flask Setup ---
app = Flask(__name__)

# --- Environment & Config Loading ---
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN") # Load HF Token

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in environment variables.")
if not HF_API_TOKEN:
    raise ValueError("HF_API_TOKEN not found in environment variables.")

PINECONE_INDEX_NAME = "medicine-info" # Or get from .env if you prefer

# --- Hugging Face Inference API Configuration ---
# Using the same model for consistency with potential existing Pinecone index
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{MODEL_ID}"
# Expected dimension for all-MiniLM-L6-v2
EXPECTED_DIMENSION = 384

# --- Removed Model Loading Section ---
# No local model loading needed

# --- Embedding API Function ---
def get_embedding_from_api(text: str) -> list[float] | None:
    """Gets sentence embedding from Hugging Face Inference API."""
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": text, "options": {"wait_for_model": True}} # wait_for_model can help if the model isn't instantly ready

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=20) # Added timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
        result = response.json()

        # HF feature-extraction pipeline returns embedding directly (sometimes nested)
        # Check if the result is a list of lists (batch) or just a list (single)
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and len(result[0]) == EXPECTED_DIMENSION:
             # It seems the API might return a list containing one embedding vector for a single input
             embedding = result[0]
        elif isinstance(result, list) and len(result) == EXPECTED_DIMENSION and isinstance(result[0], float):
             # It might return just the embedding vector list directly
             embedding = result
        else:
             # Log unexpected format for debugging
             print(f"Unexpected API response format: {type(result)}")
             if isinstance(result, list) and len(result) > 0:
                 print(f"First element type: {type(result[0])}, Length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
             return None # Indicate failure due to unexpected format

        # Optional: Double-check dimension
        if len(embedding) != EXPECTED_DIMENSION:
            print(f"Warning: Received embedding dimension {len(embedding)}, expected {EXPECTED_DIMENSION}")
            # Decide whether to return None or the embedding anyway
            # return None
        return embedding

    except requests.exceptions.Timeout:
        print(f"Error: Timeout contacting Hugging Face API at {HF_API_URL}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Hugging Face API: {e}")
        # Log the response content if possible and safe
        try:
            print(f"API Response Status: {e.response.status_code}")
            print(f"API Response Body: {e.response.text}")
        except AttributeError:
            pass # No response attached to exception
        return None
    except Exception as e: # Catch potential JSON decoding errors or other issues
        print(f"An unexpected error occurred during embedding generation: {e}")
        return None


# --- Pinecone Initialization (Function for clarity) ---
def init_pinecone():
    """Initializes and returns the Pinecone index."""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        # Optional: Check if index exists
        # if PINECONE_INDEX_NAME not in pc.list_indexes().names:
        #     print(f"Index '{PINECONE_INDEX_NAME}' not found. Creating it...")
        #     # Note: We need the dimension here if creating the index!
        #     pc.create_index(
        #          PINECONE_INDEX_NAME,
        #          dimension=EXPECTED_DIMENSION, # Use the known dimension
        #          metric='cosine',
        #          spec=ServerlessSpec(cloud='aws', region='us-east-1') # Choose appropriate cloud/region
        #      )
        #     print(f"Index '{PINECONE_INDEX_NAME}' created.")
        return pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        print(f"Error initializing Pinecone: {e}")
        return None

# --- Routes ---
@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Handles the medicine search query using API for embeddings."""
    # No local model check needed anymore

    try:
        data = request.get_json()
        medicine_name = data.get('medicine_name', '').strip()

        if not medicine_name:
            return jsonify({"error": "Medicine name is required"}), 400

        # Initialize Pinecone Index for this request
        index = init_pinecone()
        if not index:
             return jsonify({"error": "Failed to connect to Pinecone index"}), 500

        # Encode the query using the API
        query_text = f"Information about the medicine: {medicine_name}"
        print(f"Getting embedding for: '{query_text}'")
        query_vector = get_embedding_from_api(query_text)

        if query_vector is None:
            # Error logged within get_embedding_from_api
            return jsonify({"error": "Failed to generate query embedding via API."}), 500

        print(f"Successfully received embedding vector (first 5 dims): {query_vector[:5]}...") # Log snippet

        # Query Pinecone
        print(f"Querying Pinecone index '{PINECONE_INDEX_NAME}'...")
        results = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True
        )
        print("Pinecone query successful.")

        if not results or not results['matches']:
            print(f"No matches found for '{medicine_name}'")
            return jsonify({"error": f"No information found for '{medicine_name}'"}), 404

        # Process the top match
        top_match = results['matches'][0]
        metadata = top_match['metadata']
        similarity = top_match['score']
        print(f"Top match found with score: {similarity:.4f}")

        # Format the information - use .get with defaults for safety
        info = {
            "id": metadata.get('id', 'N/A'),
            "name": metadata.get('name', medicine_name), # Default to query if name missing
            "substitutes": [metadata.get(f'substitute{i}') for i in range(5) if metadata.get(f'substitute{i}')],
            "side_effects": [metadata.get(f'sideEffect{i}') for i in range(5) if metadata.get(f'sideEffect{i}')],
            "uses": [metadata.get(f'use{i}') for i in range(5) if metadata.get(f'use{i}')],
            "chemical_class": metadata.get('Chemical Class', 'N/A'),
            "habit_forming": metadata.get('Habit Forming', 'N/A'),
            "therapeutic_class": metadata.get('Therapeutic Class', 'N/A'),
            "action_class": metadata.get('Action Class', 'N/A'),
            "match_score": f"{similarity:.2f}" # Format score
        }

        # Add fallback messages if lists are empty
        if not info["substitutes"]: info["substitutes"] = ["No specific substitutes listed."]
        if not info["side_effects"]: info["side_effects"] = ["No specific side effects listed."]
        if not info["uses"]: info["uses"] = ["No specific uses listed."]

        print(f"Prepared response data for {info.get('name', 'N/A')}")
        return jsonify(info)

    except Exception as e:
        print(f"An unexpected error occurred during search: {e}") # Log the error server-side
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True) # debug=True is useful for development, turn off for production