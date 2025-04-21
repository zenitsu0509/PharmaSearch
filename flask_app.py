from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# --- Basic Flask Setup ---
app = Flask(__name__)

# --- Environment & Config Loading ---
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in environment variables.")
PINECONE_INDEX_NAME = "medicine-info" # Or get from .env if you prefer

# --- Model Loading (Load once at startup) ---
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Sentence Transformer model loaded successfully.")
except Exception as e:
    print(f"Error loading Sentence Transformer model: {e}")
    # Depending on your needs, you might want to exit or handle this differently
    model = None # Indicate model failed to load

# --- Pinecone Initialization (Function for clarity) ---
def init_pinecone():
    """Initializes and returns the Pinecone index."""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        # Optional: Check if index exists and maybe create it if it doesn't
        # if PINECONE_INDEX_NAME not in pc.list_indexes().names:
        #     print(f"Index '{PINECONE_INDEX_NAME}' not found. Please create it.")
        #     # Or handle creation:
        #     # pc.create_index(PINECONE_INDEX_NAME, dimension=model.get_sentence_embedding_dimension(), metric='cosine', spec=ServerlessSpec(cloud='aws', region='us-east-1'))
        #     return None # Or raise an error
        return pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        print(f"Error initializing Pinecone: {e}")
        return None

# Initialize index globally or per request?
# For efficiency, especially with serverless, initializing once might be okay,
# but connections can timeout. Initializing per request is safer but slower.
# Let's stick to per-request for robustness based on original code.

# --- Routes ---
@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Handles the medicine search query."""
    if not model:
        return jsonify({"error": "Model not loaded. Cannot perform search."}), 500

    try:
        data = request.get_json()
        medicine_name = data.get('medicine_name', '').strip() # Add strip()

        if not medicine_name:
            return jsonify({"error": "Medicine name is required"}), 400

        # Initialize Pinecone Index for this request
        index = init_pinecone()
        if not index:
             return jsonify({"error": "Failed to connect to Pinecone index"}), 500

        # Encode the query
        # Using a slightly more descriptive query might help retrieval
        query_text = f"Information about the medicine: {medicine_name}"
        query_vector = model.encode(query_text).tolist()

        # Query Pinecone
        results = index.query(
            vector=query_vector,
            top_k=5, # Get a few results to potentially show alternatives if needed
            include_metadata=True
        )

        if not results or not results['matches']:
            return jsonify({"error": f"No information found for '{medicine_name}'"}), 404

        # Process the top match
        top_match = results['matches'][0]
        metadata = top_match['metadata']
        similarity = top_match['score']

        # Format the information - use .get with defaults for safety
        info = {
            "id": metadata.get('id', 'N/A'),
            "name": metadata.get('name', medicine_name), # Default to query if name missing
            "substitutes": [metadata.get(f'substitute{i}') for i in range(5) if metadata.get(f'substitute{i}')],
            "side_effects": [metadata.get(f'sideEffect{i}') for i in range(42) if metadata.get(f'sideEffect{i}')], # 42 seems high, check dataset source
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


        return jsonify(info)

    except Exception as e:
        print(f"An error occurred during search: {e}") # Log the error server-side
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # The app will automatically look for 'templates' and 'static' folders
    # No need to explicitly create them here anymore
    app.run(debug=True) # debug=True is useful for development, turn off for production