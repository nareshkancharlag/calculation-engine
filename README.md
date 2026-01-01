# Tax RAG Application

A Retrieval-Augmented Generation (RAG) application that calculates taxes based on plain text rules using FastAPI, Milvus, and Ollama.

## Prerequisites
- Python 3.8+
- [Ollama](https://ollama.com/) installed and running.
- Pull necessary models:
  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3.2
  ```

## Setup
1.  Clone/Download the repository.
2.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r backend/requirements.txt
    pip install milvus-lite
    ```

## Running the Application

### 1. Start the Backend
Open a terminal, navigate to the project root, and run:
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000`.

### 2. Run the Frontend
Since the frontend is a static HTML file, you can simply open it in your browser.
From a new terminal tab in the project root:
```bash
open frontend/index.html
```
(On Windows use `start frontend/index.html`, on Linux use `xdg-open frontend/index.html`)

## Usage
1.  On the web page, click **"Ingest Rules (Admin)"** to load the rules into the database.
2.  Enter your tax query in the text box and click **"Calculate Tax"**.
