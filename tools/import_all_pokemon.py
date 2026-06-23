import requests
import sqlite3
import time

DB = "pokedex.db"
BASE = "https://pokeapi.co/api/v2"


def get_pokemon_list(limit=151):
    r = requests.get(f"{BASE}/pokemon?limit={limit}")
    r.raise_for_status()
    return r.json()["results"]


def get_pokemon(url):
    r = requests.get(url)
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

    print("Fetching Pokémon list...")
    pokemon_list = get_pokemon_list(limit=151)  # start with Gen 1

    for i, p in enumerate(pokemon_list):
        try:
            data = get_pokemon(p["url"])
            save(cur, data)

            print(f"{i+1}/151 Imported: {data['name']}")

            time.sleep(0.2)  # avoid rate limit

        except Exception as e:
            print("Failed:", p["name"], e)

    conn.commit()
    conn.close()

    print("Done importing Pokémon!")


if __name__ == "__main__":
    main()
