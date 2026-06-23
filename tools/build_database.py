import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests
from db.init import migrate
from core.db import connect

BASE = "https://pokeapi.co/api/v2"
DATA_DIR = Path(__file__).resolve().parent.parent


def fetch_resource(url, session):
    response = session.get(url)
    response.raise_for_status()
    return response.json()


def list_resources(endpoint, session, limit=100000):
    url = f"{BASE}/{endpoint}?limit={limit}"
    data = fetch_resource(url, session)
    return data.get("results", [])


def load_abilities(session, conn):
    print("Loading abilities...")
    abilities = list_resources("ability", session)
    with conn:
        conn.execute("DELETE FROM abilities")
        for item in abilities:
            data = fetch_resource(item["url"], session)
            name = data["name"].replace('-', ' ')
            generation = data["generation"]["name"].replace('-', ' ')
            effect_entries = data.get("effect_entries", [])
            effect_text = ""
            short_effect = ""
            for entry in effect_entries:
                if entry["language"]["name"] == "en":
                    effect_text = entry.get("effect", "")
                    short_effect = entry.get("short_effect", "")
                    break
            conn.execute(
                "INSERT OR REPLACE INTO abilities (name, generation, short_effect, effect) VALUES (?, ?, ?, ?)",
                (name, generation, short_effect, effect_text)
            )
    print(f"Loaded {len(abilities)} abilities.")


def load_pokemon(session, conn):
    print("Loading pokemon...")
    entries = list_resources("pokemon", session)
    with conn:
        conn.execute("DELETE FROM pokemon")
        conn.execute("DELETE FROM pokemon_breeding")
        for idx, item in enumerate(entries, 1):
            data = fetch_resource(item["url"], session)
            name = data["name"].replace('-', ' ')
            types = [t["type"]["name"] for t in data.get("types", [])]
            stats = {stat["stat"]["name"]: stat["base_stat"] for stat in data.get("stats", [])}
            abilities = [a["ability"]["name"].replace('-', ' ') for a in data.get("abilities", [])]
            ability_1 = abilities[0] if len(abilities) > 0 else None
            ability_2 = abilities[1] if len(abilities) > 1 else None
            hidden_ability = next((a["ability"]["name"].replace('-', ' ') for a in data.get("abilities", []) if a.get("is_hidden")), None)
            
            # Fetch generation from pokemon-species endpoint
            generation = None
            species_name = None
            gender_rate = None
            egg_cycles = None
            try:
                species_url = f"{BASE}/pokemon-species/{data.get('id')}"
                species_data = fetch_resource(species_url, session)
                species_name = species_data.get("name", "").replace('-', ' ')
                if "generation" in species_data:
                    generation = species_data["generation"]["name"].replace('-', ' ')
                gender_rate = species_data.get("gender_rate")
                egg_cycles = species_data.get("hatch_counter")
            except Exception as e:
                pass  # If species fetch fails, generation will be None

            if species_name:
                conn.execute(
                    "INSERT OR REPLACE INTO pokemon_breeding (pokemon, gender_rate, egg_cycles) VALUES (?, ?, ?)",
                    (species_name, gender_rate, egg_cycles),
                )
            
            conn.execute(
                "INSERT OR REPLACE INTO pokemon (name, type1, type2, hp, attack, defense, sp_attack, sp_defense, speed, ability_1, ability_2, hidden_ability, base_experience, height, weight, generation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    types[0] if types else None,
                    types[1] if len(types) > 1 else None,
                    stats.get("hp"),
                    stats.get("attack"),
                    stats.get("defense"),
                    stats.get("special-attack"),
                    stats.get("special-defense"),
                    stats.get("speed"),
                    ability_1,
                    ability_2,
                    hidden_ability,
                    data.get("base_experience"),
                    data.get("height"),
                    data.get("weight"),
                    generation,
                ),
            )
            if idx % 50 == 0:
                print(f"  {idx}/{len(entries)} pokemon loaded...")
            time.sleep(0.01)
    print(f"Loaded {len(entries)} pokemon.")


def load_moves(session, conn):
    print("Loading moves...")
    moves = list_resources("move", session)
    with conn:
        conn.execute("DELETE FROM moves")
        for idx, item in enumerate(moves, 1):
            data = fetch_resource(item["url"], session)
            name = data["name"].replace('-', ' ')
            effect_entries = data.get("effect_entries", [])
            effect_text = ""
            for entry in effect_entries:
                if entry["language"]["name"] == "en":
                    effect_text = entry.get("effect", "")
                    break
            category = data.get("damage_class", {}).get("name")
            conn.execute(
                "INSERT OR REPLACE INTO moves (name, type, category, power, accuracy, pp, generation, effect) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    data.get("type", {}).get("name"),
                    category,
                    data.get("power"),
                    data.get("accuracy"),
                    data.get("pp"),
                    data.get("generation", {}).get("name"),
                    effect_text,
                ),
            )
            if idx % 100 == 0:
                print(f"  {idx}/{len(moves)} moves loaded...")
            time.sleep(0.01)
    print(f"Loaded {len(moves)} moves.")


def load_items(session, conn):
    print("Loading items...")
    items = list_resources("item", session)
    with conn:
        conn.execute("DELETE FROM items")
        for idx, item in enumerate(items, 1):
            data = fetch_resource(item["url"], session)
            name = data.get("name", "").replace('-', ' ')
            effect_entries = data.get("effect_entries", [])
            effect_text = ""
            short_effect = ""
            for entry in effect_entries:
                if entry.get("language", {}).get("name") == "en":
                    effect_text = entry.get("effect", "")
                    short_effect = entry.get("short_effect", "")
                    break
            conn.execute(
                "INSERT OR REPLACE INTO items (name, category, cost, fling_power, fling_effect, generation, short_effect, effect) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    data.get("category", {}).get("name"),
                    data.get("cost"),
                    data.get("fling_power"),
                    data.get("fling_effect", {}).get("name") if data.get("fling_effect") else None,
                    data.get("generation", {}).get("name"),
                    short_effect,
                    effect_text,
                )
            )
            if idx % 100 == 0:
                print(f"  {idx}/{len(items)} items loaded...")
            time.sleep(0.005)
    print(f"Loaded {len(items)} items.")


def load_apricorn_recipes(conn):
    """Load apricorn crafting recipes from data/apricorn_recipes.json."""
    recipes_file = Path(__file__).resolve().parent.parent / 'data' / 'apricorn_recipes.json'
    if not recipes_file.exists():
        print("No data/apricorn_recipes.json found - skipping apricorn recipe import.")
        return

    print("Loading apricorn crafting recipes...")
    with conn:
        conn.execute("DELETE FROM apricorn_recipes")
        with open(recipes_file, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        row_count = 0
        for recipe in data:
            game = recipe.get('game')
            item_name = recipe.get('item')
            notes = recipe.get('notes')
            for ingredient in recipe.get('ingredients', []):
                conn.execute(
                    "INSERT INTO apricorn_recipes (game, item, ingredient, quantity, notes) VALUES (?, ?, ?, ?, ?)",
                    (
                        game,
                        item_name,
                        ingredient.get('name'),
                        ingredient.get('quantity'),
                        notes,
                    ),
                )
                row_count += 1
    print(f"Loaded {len(data)} apricorn recipes ({row_count} ingredient rows).")


def load_egg_groups(session, conn):
    print("Loading egg groups...")
    groups = list_resources("egg-group", session)
    with conn:
        conn.execute("DELETE FROM egg_groups")
        conn.execute("DELETE FROM pokemon_egg_groups")
        for item in groups:
            data = fetch_resource(item["url"], session)
            group_name = data["name"].replace('-', ' ')
            conn.execute(
                "INSERT OR REPLACE INTO egg_groups (name) VALUES (?)",
                (group_name,),
            )
            for pokemon_entry in data.get("pokemon_species", []):
                pokemon_name = pokemon_entry["name"].replace('-', ' ')
                conn.execute(
                    "INSERT INTO pokemon_egg_groups (pokemon, egg_group) VALUES (?, ?)",
                    (pokemon_name, group_name),
                )
    print(f"Loaded {len(groups)} egg groups.")


def load_location_encounters(session, conn):
    print("Loading location encounters...")
    areas = list_resources("location-area", session)
    with conn:
        conn.execute("DELETE FROM encounters")
        for idx, item in enumerate(areas, 1):
            area_data = fetch_resource(item["url"], session)
            route_name = area_data.get("location", {}).get("name", "").replace('-', ' ')
            location_area = area_data.get("name", "").replace('-', ' ')
            location_name = route_name or location_area
            for encounter in area_data.get("pokemon_encounters", []):
                pokemon_name = encounter.get("pokemon", {}).get("name", "").replace('-', ' ')
                for version_detail in encounter.get("version_details", []):
                    game = version_detail.get("version", {}).get("name")
                    for encounter_detail in version_detail.get("encounter_details", []):
                        conn.execute(
                            "INSERT INTO encounters (game, route, location_name, location_area, pokemon, min_level, max_level, chance, method) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                game,
                                route_name,
                                location_name,
                                location_area,
                                pokemon_name,
                                encounter_detail.get("min_level"),
                                encounter_detail.get("max_level"),
                                encounter_detail.get("chance"),
                                encounter_detail.get("method", {}).get("name"),
                            ),
                        )
            if idx % 100 == 0:
                print(f"  {idx}/{len(areas)} location areas loaded...")
            time.sleep(0.01)
    print(f"Loaded {len(areas)} location encounters.")


def load_machines(session, conn):
    print("Loading TM/HM machines...")
    machines = list_resources("machine", session)
    vgroup_cache = {}
    with conn:
        conn.execute("DELETE FROM tms")
        for idx, item in enumerate(machines, 1):
            try:
                data = fetch_resource(item["url"], session)
            except Exception:
                continue
            item_name = data.get("item", {}).get("name")
            move_name = data.get("move", {}).get("name")
            vgroup = data.get("version_group", {}).get("name")
            if not item_name or not move_name or not vgroup:
                continue
            if vgroup not in vgroup_cache:
                vg_data = fetch_resource(data.get("version_group", {})["url"], session)
                versions = [v["name"] for v in vg_data.get("versions", [])]
                vgroup_cache[vgroup] = versions
            versions = vgroup_cache.get(vgroup, [])
            for ver in versions:
                conn.execute(
                    "INSERT INTO tms (game, code, move) VALUES (?, ?, ?)",
                    (ver, item_name, move_name),
                )
            if idx % 200 == 0:
                print(f"  {idx}/{len(machines)} machines processed...")
            time.sleep(0.005)
    print(f"Loaded {len(machines)} machines.")


def load_pokemon_moves(session, conn):
    print("Loading pokemon learnsets...")
    entries = list_resources("pokemon", session)
    vgroup_cache = {}
    allowed_methods = {"level-up", "machine", "tutor"}

    with conn:
        conn.execute("DELETE FROM pokemon_moves")
        for idx, item in enumerate(entries, 1):
            try:
                data = fetch_resource(item["url"], session)
            except Exception:
                continue

            pokemon_name = data.get("name", "").replace('-', ' ')
            for move_entry in data.get("moves", []):
                move_name = move_entry.get("move", {}).get("name", "").replace('-', ' ')
                for detail in move_entry.get("version_group_details", []):
                    method = detail.get("move_learn_method", {}).get("name")
                    if method not in allowed_methods:
                        continue

                    level = detail.get("level_learned_at")
                    version_group = detail.get("version_group", {}).get("name")
                    version_group_url = detail.get("version_group", {}).get("url")
                    if not version_group:
                        continue

                    if version_group not in vgroup_cache:
                        versions = []
                        if version_group_url:
                            try:
                                vg_data = fetch_resource(version_group_url, session)
                                versions = [v.get("name") for v in vg_data.get("versions", []) if v.get("name")]
                            except Exception:
                                versions = []
                        vgroup_cache[version_group] = versions or [version_group]

                    for game in vgroup_cache.get(version_group, [version_group]):
                        conn.execute(
                            "INSERT INTO pokemon_moves (pokemon, move, game, method, level) VALUES (?, ?, ?, ?, ?)",
                            (pokemon_name, move_name, game, method, level),
                        )

            if idx % 50 == 0:
                print(f"  {idx}/{len(entries)} pokemon learnsets loaded...")
            time.sleep(0.01)
    print(f"Loaded learnsets for {len(entries)} pokemon.")


def load_evolutions(session, conn):
    """Load evolution chains from the PokeAPI evolution-chain endpoint.
    Stores rows in `evolutions(pokemon, evolves_to, method, min_level)`.
    """
    print("Loading evolutions via evolution-chain...")
    chains = list_resources("evolution-chain", session)
    with conn:
        conn.execute("DELETE FROM evolutions")
        for idx, item in enumerate(chains, 1):
            try:
                data = fetch_resource(item["url"], session)
            except Exception:
                continue
            def walk(node):
                base = node.get('species', {}).get('name', '').replace('-', ' ')
                for evo in node.get('evolves_to', []) or []:
                    target = evo.get('species', {}).get('name', '').replace('-', ' ')
                    details = evo.get('evolution_details', []) or []
                    if details:
                        for d in details:
                            method = d.get('trigger', {}).get('name')
                            min_level = d.get('min_level')
                            item = d.get('item', {}).get('name') if d.get('item') else None
                            held_item = d.get('held_item', {}).get('name') if d.get('held_item') else None
                            min_happiness = d.get('min_happiness')
                            min_affection = d.get('min_affection')
                            min_beauty = d.get('min_beauty')
                            known_move = d.get('known_move', {}).get('name') if d.get('known_move') else None
                            known_move_type = d.get('known_move_type', {}).get('name') if d.get('known_move_type') else None
                            location = d.get('location', {}).get('name') if d.get('location') else None
                            trade_species = d.get('trade_species', {}).get('name') if d.get('trade_species') else None
                            party_species = d.get('party_species', {}).get('name') if d.get('party_species') else None
                            party_type = d.get('party_type', {}).get('name') if d.get('party_type') else None
                            relative_physical_stats = d.get('relative_physical_stats')
                            time_of_day = d.get('time_of_day')
                            needs_overworld_rain = 1 if d.get('needs_overworld_rain') else 0
                            turn_upside_down = 1 if d.get('turn_upside_down') else 0
                            conn.execute(
                                "INSERT INTO evolutions (pokemon, evolves_to, method, min_level, item, held_item, min_happiness, min_affection, min_beauty, known_move, known_move_type, location, trade_species, party_species, party_type, relative_physical_stats, time_of_day, needs_overworld_rain, turn_upside_down) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    base,
                                    target,
                                    method,
                                    min_level,
                                    item,
                                    held_item,
                                    min_happiness,
                                    min_affection,
                                    min_beauty,
                                    known_move,
                                    known_move_type,
                                    location,
                                    trade_species,
                                    party_species,
                                    party_type,
                                    relative_physical_stats,
                                    time_of_day,
                                    needs_overworld_rain,
                                    turn_upside_down,
                                ),
                            )
                    else:
                        conn.execute(
                            "INSERT INTO evolutions (pokemon, evolves_to, method, min_level, item, held_item, min_happiness, min_affection, min_beauty, known_move, known_move_type, location, trade_species, party_species, party_type, relative_physical_stats, time_of_day, needs_overworld_rain, turn_upside_down) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (base, target, None, None, None, None, None, None, None, None, None, None, None, None, None, None, '', 0, 0),
                        )
                    walk(evo)
            walk(data.get('chain', {}))
            if idx % 200 == 0:
                print(f"  {idx}/{len(chains)} chains processed...")
            time.sleep(0.005)
    print(f"Loaded {len(chains)} evolution chains.")


def load_gyms(session, conn):
    """Load gym leader data from data/gyms.json if present.
    The file should be an array of objects with keys: game, gym_number, leader, city, type, badge, team (list of pokemon names in order).
    """
    import os, json
    gyms_file = Path(__file__).resolve().parent.parent / 'data' / 'gyms.json'
    if not gyms_file.exists():
        print("No data/gyms.json found — skipping gym import.")
        return

    print("Loading gyms from data/gyms.json...")
    with conn:
        conn.execute("DELETE FROM gyms")
        conn.execute("DELETE FROM gym_teams")
        with open(gyms_file, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            for entry in data:
                game = entry.get('game')
                gym_number = entry.get('gym_number')
                leader = entry.get('leader')
                city = entry.get('city')
                gtype = entry.get('type')
                badge = entry.get('badge')
                conn.execute(
                    "INSERT INTO gyms (game, gym_number, leader, city, type, badge) VALUES (?, ?, ?, ?, ?, ?)",
                    (game, gym_number, leader, city, gtype, badge),
                )
                team = entry.get('team', [])
                for idx, p in enumerate(team, 1):
                    conn.execute(
                        "INSERT INTO gym_teams (game, gym_number, pokemon, position) VALUES (?, ?, ?, ?)",
                        (game, gym_number, p, idx),
                    )
    print(f"Loaded {len(data)} gyms from data/gyms.json")


def main():
    migrate()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    with connect() as conn:
        load_abilities(session, conn)
        load_pokemon(session, conn)
        load_moves(session, conn)
        load_items(session, conn)
        load_egg_groups(session, conn)
        load_location_encounters(session, conn)
        load_machines(session, conn)
        load_pokemon_moves(session, conn)
        load_gyms(session, conn)
        load_evolutions(session, conn)
        load_apricorn_recipes(conn)
    print("Database build complete. Run python main.py to use the offline Pokédex.")


if __name__ == "__main__":
    main()
