import os
import pandas as pd
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import numpy as np
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

# Initialize Pinecone
def init_pinecone():
    # Create a Pinecone instance using the new API
    pc = Pinecone(
        api_key=os.getenv("PINECONE_API_KEY")
    )
    index_name = "medicine-info"
    
    # Check if index exists, if not create it
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=384,  # Using 'all-MiniLM-L6-v2' model which has 384 dimensions
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",  # or "gcp", depending on your preference
                region="us-east-1"  # choose an appropriate region
            )
        )
    
    # Get the index
    return pc.Index(index_name)

# Load the model for encoding text to vectors
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to process and upload medicine data to Pinecone
def upload_medicine_data(data_file, index):
    # Read medicine data
    df = pd.read_csv(data_file)
    
    # Process each medicine
    batch_size = 100
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        batch_records = []
        
        for _, row in batch.iterrows():
            # Create a text representation of the medicine
            medicine_name = str(row['name'])
            medicine_text = f"Medicine: {medicine_name}"
            
            # Create vector embedding for the medicine name
            vector = model.encode(medicine_text).tolist()
            
            # Prepare metadata (all fields from the row)
            metadata = {col: str(row[col]) for col in df.columns}
            
            # Create the record
            record = {
                'id': str(row['id']),
                'values': vector,
                'metadata': metadata
            }
            
            batch_records.append(record)
        
        # Upsert batch to Pinecone
        index.upsert(batch_records)
    
    print(f"Uploaded {len(df)} medicines to Pinecone")

# Function to query medicine information
def query_medicine_info(medicine_name, index):
    # Create vector embedding for the query
    query_vector = model.encode(f"Medicine: {medicine_name}").tolist()
    
    # Query Pinecone
    results = index.query(
        vector=query_vector,
        top_k=5,
        include_metadata=True
    )
    
    return results

# Function to format and display medicine information
def display_medicine_info(results):
    if not results['matches']:
        return "No medicine found matching the query."
    
    # Get the top match
    top_match = results['matches'][0]
    metadata = top_match['metadata']
    similarity = top_match['score']
    
    # Format the information
    info = {
        "ID": metadata.get('id', 'N/A'),
        "Name": metadata.get('name', 'N/A'),
        "Substitutes": [metadata.get(f'substitute{i}', '') for i in range(5) if metadata.get(f'substitute{i}', '')],
        "Side Effects": [metadata.get(f'sideEffect{i}', '') for i in range(5) if metadata.get(f'sideEffect{i}', '')],
        "Uses": [metadata.get(f'use{i}', '') for i in range(5) if metadata.get(f'use{i}', '')],
        "Chemical Class": metadata.get('Chemical Class', 'N/A'),
        "Habit Forming": metadata.get('Habit Forming', 'N/A'),
        "Therapeutic Class": metadata.get('Therapeutic Class', 'N/A'),
        "Action Class": metadata.get('Action Class', 'N/A'),
        "Match Score": f"{similarity:.2f}"
    }
    
    return info

def main():
    # Initialize Pinecone
    index = init_pinecone()
    
    # Upload data from specified file path
    data_file = "/hydra2-prev/home/compute/workspace_himanshu/meta-asr/medicine_dataset.csv"
    upload_medicine_data(data_file, index)
    
    # Query loop
    while True:
        query = input("\nEnter medicine name to search (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        
        results = query_medicine_info(query, index)
        info = display_medicine_info(results)
        
        if isinstance(info, str):
            print(info)
        else:
            print("\n=== Medicine Information ===")
            print(f"ID: {info['ID']}")
            print(f"Name: {info['Name']}")
            
            print("\nSubstitutes:")
            for sub in info['Substitutes']:
                print(f"- {sub}")
            
            print("\nSide Effects:")
            for effect in info['Side Effects']:
                print(f"- {effect}")
            
            print("\nUses:")
            for use in info['Uses']:
                print(f"- {use}")
            
            print(f"\nChemical Class: {info['Chemical Class']}")
            print(f"Habit Forming: {info['Habit Forming']}")
            print(f"Therapeutic Class: {info['Therapeutic Class']}")
            print(f"Action Class: {info['Action Class']}")
            print(f"\nMatch Score: {info['Match Score']}")

if __name__ == "__main__":
    main()