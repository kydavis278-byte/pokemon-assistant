from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from core.assistant import interactive_handle

app = FastAPI()

# -----------------------------
# TERMINAL UI (HOME PAGE)
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pokédex Terminal</title>
        <style>
            body {
                background: #0d0d0d;
                color: #00ff88;
                font-family: monospace;
                margin: 0;
                padding: 20px;
            }
            #terminal {
                max-width: 800px;
                margin: auto;
            }
            #output {
                white-space: pre-wrap;
                border: 1px solid #00ff88;
                padding: 10px;
                height: 400px;
                overflow-y: auto;
                margin-bottom: 10px;
            }
            input {
                width: 80%;
                padding: 10px;
                background: black;
                color: #00ff88;
                border: 1px solid #00ff88;
                font-family: monospace;
            }
            button {
                padding: 10px;
                background: #00ff88;
                border: none;
                cursor: pointer;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <div id="terminal">
            <h2>Pokédex Terminal</h2>
            <div id="output">Welcome to Pokédex Assistant\nType a query below...\n\n</div>

            <input id="input" placeholder="Ask something..." />
            <button onclick="send()">Enter</button>
        </div>

        <script>
            async function send() {
                const input = document.getElementById("input");
                const output = document.getElementById("output");

                const q = input.value;
                if (!q) return;

                output.innerText += "\\n> " + q + "\\n";

                const res = await fetch("/query?q=" + encodeURIComponent(q));
                const data = await res.json();

                output.innerText += data.result + "\\n";
                output.scrollTop = output.scrollHeight;

                input.value = "";
            }

            document.getElementById("input").addEventListener("keydown", function(e) {
                if (e.key === "Enter") {
                    send();
                }
            });
        </script>
    </body>
    </html>
    """

# -----------------------------
# API ENDPOINT
# -----------------------------
@app.get("/query")
def query(q: str = Query(...)):
    try:
        result, _context = interactive_handle(q, None)
        return {
            "query": q,
            "result": result
        }
    except Exception as e:
        return {
            "query": q,
            "error": str(e)
        }
