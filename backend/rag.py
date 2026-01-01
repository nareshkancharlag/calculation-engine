import os
import re
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)
import ollama

# Constants
MILVUS_URI = "./milvus.db"
COLLECTION_NAME = "tax_rules"
EMBEDDING_MODEL = "nomic-embed-text"
GENERATION_MODEL = "llama3.2"
EMBEDDING_DIM = 768  # nomic-embed-text has 768 dimensions

def connect_to_milvus():
    try:
        connections.connect("default", uri=MILVUS_URI)
        print("Connected to Milvus (Lite)")
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        raise

def create_collection_if_not_exists():
    connect_to_milvus()
    
    if utility.has_collection(COLLECTION_NAME):
        collection = Collection(COLLECTION_NAME)
        # Check if dim matches, if not drop and recreate? For simplicity, assumes correct.
        return collection
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="rule_id", dtype=DataType.INT64),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=5000),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    ]
    
    schema = CollectionSchema(fields, "Taxation rules collection")
    collection = Collection(COLLECTION_NAME, schema)
    
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    collection.load()
    print(f"Collection {COLLECTION_NAME} created and loaded")
    return collection

def parse_rules(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    
    # Split by "Rule_ID:"
    # We want to capture the ID and the content following it.
    # The file format seems to be:
    # Rule_ID: <number>
    # <content>
    # Rule_ID: <number>
    
    rules = []
    # Regex to find all matches of Rule_ID: (\d+)
    matches = list(re.finditer(r"Rule_ID:\s*(\d+)", content))
    
    for i, match in enumerate(matches):
        start = match.start()
        rule_id = int(match.group(1))
        
        # End is the start of the next match, or end of file
        end = matches[i+1].start() if i + 1 < len(matches) else len(content)
        
        rule_text = content[start:end].strip()
        rules.append({"rule_id": rule_id, "content": rule_text})
        
    return rules

def ingest_rules(file_path="rules_in_plain_text.txt", clear_collection=False):
    if clear_collection:
        connect_to_milvus()
        if utility.has_collection(COLLECTION_NAME):
            utility.drop_collection(COLLECTION_NAME)
            print(f"Collection {COLLECTION_NAME} dropped.")

    collection = create_collection_if_not_exists()
    
    rules = parse_rules(file_path)
    
    data = [
        [], # rule_id
        [], # content
        []  # embedding
    ]
    
    for rule in rules:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=rule["content"])
        embedding = response["embedding"]
        
        data[0].append(rule["rule_id"])
        data[1].append(rule["content"])
        data[2].append(embedding)
    
    if data[0]:
        collection.insert(data)
        collection.flush()
        print(f"Ingested {len(rules)} rules.")
    return len(rules)

def get_next_rule_id(file_path):
    try:
        with open(file_path, "r") as f:
            content = f.read()
        matches = list(re.finditer(r"Rule_ID:\s*(\d+)", content))
        if not matches:
            return 1
        ids = [int(m.group(1)) for m in matches]
        return max(ids) + 1
    except FileNotFoundError:
        return 1

def add_rule(new_rule_content: str, file_path="../rules_in_plain_text.txt"):
    # 1. Determine next ID
    next_id = get_next_rule_id(file_path)
    
    # 2. Format the new rule block
    # Ensure double newlines for separation
    formatted_rule = f"\n\nRule_ID: {next_id}\n{new_rule_content.strip()}"
    
    # 3. Append to file
    with open(file_path, "a") as f:
        f.write(formatted_rule)
    
    # 4. Ingest into Milvus
    connect_to_milvus()
    collection = Collection(COLLECTION_NAME)
    
    # Create the rule object to match what parse_rules produces
    # NOTE: The content stored in DB usually excludes "Rule_ID: X". 
    # parse_rules captures content AFTER Rule_ID.
    # So we should store just the content provided by user.
    
    response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=new_rule_content)
    embedding = response["embedding"]
    
    data = [
        [next_id],          # rule_id
        [new_rule_content], # content
        [embedding]         # embedding
    ]
    
    collection.insert(data)
    collection.flush()
    print(f"Added Rule ID {next_id} to Milvus.")
    return next_id

def get_tax_calculation(query: str):
    connect_to_milvus()
    collection = Collection(COLLECTION_NAME)
    collection.load()
    
    # Embed query
    response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=query)
    query_emb = response["embedding"]
    
    # Search
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_emb],
        anns_field="embedding",
        param=search_params,
        limit=1,
        output_fields=["content", "rule_id"]
    )
    
    if not results or not results[0]:
        return {"error": "No relevant rule found"}
    
    hit = results[0][0]
    context = hit.entity.get("content")
    
    prompt = f"""
You are a generic calculation assistant.
Use the following rule context to answer the user query.
Context:
{context}

Query: {query}

Instructions:
1. Extract the numeric values (price, age, quantity, etc.) from the User Query.
2. If the User Query DOES NOT contain the necessary BASE value (like price, sum assured, etc.), YOU MUST assume the value from the 'Context' (Rule Example or Scenario).
3. IF you assumed a BASE value, you MUST explicitly state in the response that "No input value given from the query, value will be assumed and taken from the default rules txt file".
4. Do NOT apply optional discounts, surcharges, or specific conditions (like "early payment discount", "membership", etc.) unless the User Query explicitly mentions them. Assume the standard/base rate otherwise.
5. Perform the calculation based on the values (either from query or assumed).

Return the answer in strict JSON format with the following keys:
- result: A short summary of the result (e.g. "Premium is $500").
- calculated_value: The final calculated number.
- explanation: A detailed explanation of the steps.
"""
    
    llm_response = ollama.chat(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )
    
    return llm_response['message']['content']
