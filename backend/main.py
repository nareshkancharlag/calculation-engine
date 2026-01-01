from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag import ingest_rules, get_tax_calculation, add_rule
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tax RAG API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CalculateRequest(BaseModel):
    text: str

class AddRuleRequest(BaseModel):
    text: str

@app.post("/add_rule")
async def add_rule_endpoint(request: AddRuleRequest):
    try:
        rule_id = add_rule(request.text)
        return {"status": "success", "message": f"Rule added successfully with ID {rule_id}"}
    except Exception as e:
        logger.error(f"Add rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_endpoint(reset: bool = True):
    try:
        count = ingest_rules("../rules_in_plain_text.txt", clear_collection=reset)
        action = "Resetted and ingested" if reset else "Ingested"
        return {"status": "success", "message": f"{action} {count} rules."}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate")
async def calculate_endpoint(request: CalculateRequest):
    try:
        # get_tax_calculation returns a string (JSON from LLM)
        # get_tax_calculation returns a string (JSON from LLM) OR a dict (error)
        llm_response = get_tax_calculation(request.text)
        
        if isinstance(llm_response, dict):
            # If it's already a dict, it's likely the error case from rag.py
            # { "error": "No relevant rule found" }
            # We should wrap it in the expected format for the frontend if needed,
            # or just return it if the frontend handles it. 
            # Frontend expects: calculated_value, result, explanation.
            if "error" in llm_response:
                 return {
                    "result": llm_response["error"],
                    "calculated_value": 0,
                    "explanation": llm_response["error"]
                }
            return llm_response

        # Try to parse it as JSON to ensure structure
        # The LLM might output text before/after JSON, we might need cleanup
        try:
            # Simple cleanup validation
            start = llm_response.find("{")
            end = llm_response.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = llm_response[start:end]
                data = json.loads(json_str)
                return data
            else:
                raise ValueError("No JSON found")
        except Exception:
            # If parsing fails, return raw string wrapped in structure
            return {
                "result": llm_response,
                "calculated_value": 0,
                "explanation": "Could not parse structured response from LLM. See raw result."
            }
            
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
