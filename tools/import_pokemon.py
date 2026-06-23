import requests
import sqlite3
import time

DB = "pokedex.db"
BASE = "https://pokeapi.co/api/v2"


def fetch_pokemon(name):
    r = requests.get(f"{BASE}/pokemon/{name}")
    r.raise_for_status()
    data = r.json()

    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}

    types = [t["type"]["name"] for t in data["types"]]

    return {
        "name": data["name"],
        "type1": types[0],
        "type2": types[1] if len(types) > 1 else None,
        "hp": stats["hp"],
        "attack": stats["attack"],
        "defense": stats["defense"],
        "sp_attack": stats["special-attack"],
        "sp_defense": stats["special-defense"],
        "speed": stats["speed"],
    }


def save(cur, p):
    cur.execute(
        """
        INSERT OR REPLACE INTO pokemon
        (name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            p["name"], p["type1"], p["type2"],
            p["hp"], p["attack"], p["defense"],
            p["sp_attack"], p["sp_defense"], p["speed"]
        )
    )


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    pokemon_list = [
        "pikachu",
        "charizard",
        "bulbasaur",
        "squirtle",
        "gengar",
        "lucario",
        "dragonite"
    ]

    for name in pokemon_list:
        try:
            p = fetch_pokemon(name)
            save(cur, p)
            print("Imported:", name)
            time.sleep(0.3)
        except Exception as e:
            print("Failed:", name, e)

    conn.commit()
    conn.close()

    print("Done importing Pokémon")


if __name__ == "__main__":
    main()
