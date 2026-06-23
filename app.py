from fastapi import FastAPI, Query

# IMPORTANT:
# Change this import to match YOUR actual file name
# examples: from main import handle_query
#           from pokedex import handle_query
#           from assistant_core import handle_query

from main import handle_query  # <-- CHANGE THIS LINE IF NEEDED

app = FastAPI()


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Pokédex Assistant API is running",
        "usage": "/query?q=charizard"
    }


@app.get("/query")
def query(q: str = Query(..., description="Pokémon query string")):
    try:
        result = handle_query(q)
        return {
            "query": q,
            "result": result
        }
    except Exception as e:
        return {
            "query": q,
            "error": str(e)
        }
