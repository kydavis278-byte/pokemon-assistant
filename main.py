from core.assistant import interactive_handle
import itertools
import threading
import time

WELCOME = """
Pokédex Assistant
Type a question like:
  - what does the ability no guard do?
  - what pokemon are in viridian forest in pokemon crystal?
  - what is charizard?
  - what does earthquake do?
Type 'exit' or 'quit' to leave.
"""

print(WELCOME.strip())
last_context = None

while True:
    try:
        query = input("pokedex> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        break

    if not query:
        continue

    if query.lower() in {"exit", "quit", "q"}:
        break

    result_holder = {}

    def _run_query():
        response, context = interactive_handle(query, last_context)
        result_holder["response"] = response
        result_holder["context"] = context

    worker = threading.Thread(target=_run_query, daemon=True)
    worker.start()

    worker.join(timeout=2.0)
    if worker.is_alive():
        spinner = itertools.cycle(["|", "/", "-", "\\"])
        while worker.is_alive():
            print(f"\rPlease wait {next(spinner)}", end="", flush=True)
            worker.join(timeout=0.12)
        print("\r" + " " * 32 + "\r", end="", flush=True)

    response = result_holder.get("response", "I couldn't complete that request.")
    last_context = result_holder.get("context")
    print()
    print(response)
    print()
