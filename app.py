from fastapi import FastAPI
from assistant import handle_query  # or whatever your main function is

app = FastAPI()

@app.get("/query")
def query(q: str):
    return {"result": handle_query(q)}
