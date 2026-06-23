from fastapi import FastAPI, Query
from core.assistant import interactive_handle

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
        response, _context = interactive_handle(q, None)

        return {
            "query": q,
            "result": response
        }

    except Exception as e:
        return {
            "query": q,
            "error": str(e)
        }
