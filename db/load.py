import sqlite3
import json

DB = "pokedex.db"

def load_abilities():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    data = json.load(open("data/abilities.json"))

    cur.execute("DELETE FROM abilities")

    for a in data:
        cur.execute(
            "INSERT INTO abilities VALUES (?, ?, ?, ?)",
            (a["id"], a["name"], a["generation"], a["effect"])
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    load_abilities()
    print("Abilities loaded")
