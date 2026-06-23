import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "pokedex.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")


def connect():
    return sqlite3.connect(DB_PATH)


def create_schema():
    with connect() as conn:
        with open(SCHEMA_PATH, encoding='utf-8') as schema_file:
            script = schema_file.read()

        for statement in script.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if statement.upper().startswith("CREATE INDEX") and "no such column" in msg:
                    continue
                if statement.upper().startswith("CREATE INDEX") and "no such table" in msg:
                    continue
                raise


def table_columns(table):
    with connect() as conn:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]


def ensure_column(table, column, definition):
    cols = table_columns(table)
    if column not in cols:
        with connect() as conn:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate():
    create_schema()
    ensure_column("abilities", "short_effect", "TEXT")
    ensure_column("pokemon", "pokedex_number", "INTEGER")
    ensure_column("pokemon", "generation", "TEXT")
    ensure_column("pokemon", "ability_1", "TEXT")
    ensure_column("pokemon", "ability_2", "TEXT")
    ensure_column("pokemon", "hidden_ability", "TEXT")
    ensure_column("pokemon", "base_experience", "INTEGER")
    ensure_column("pokemon", "height", "INTEGER")
    ensure_column("pokemon", "weight", "INTEGER")
    ensure_column("moves", "type", "TEXT")
    ensure_column("moves", "category", "TEXT")
    ensure_column("moves", "power", "INTEGER")
    ensure_column("moves", "accuracy", "INTEGER")
    ensure_column("moves", "pp", "INTEGER")
    ensure_column("moves", "generation", "TEXT")
    ensure_column("moves", "effect", "TEXT")
    ensure_column("items", "name", "TEXT")
    ensure_column("items", "category", "TEXT")
    ensure_column("items", "cost", "INTEGER")
    ensure_column("items", "fling_power", "INTEGER")
    ensure_column("items", "fling_effect", "TEXT")
    ensure_column("items", "generation", "TEXT")
    ensure_column("items", "short_effect", "TEXT")
    ensure_column("items", "effect", "TEXT")
    ensure_column("apricorn_recipes", "game", "TEXT")
    ensure_column("apricorn_recipes", "item", "TEXT")
    ensure_column("apricorn_recipes", "ingredient", "TEXT")
    ensure_column("apricorn_recipes", "quantity", "INTEGER")
    ensure_column("apricorn_recipes", "notes", "TEXT")
    ensure_column("pokemon_breeding", "pokemon", "TEXT")
    ensure_column("pokemon_breeding", "gender_rate", "INTEGER")
    ensure_column("pokemon_breeding", "egg_cycles", "INTEGER")
    ensure_column("encounters", "route", "TEXT")
    ensure_column("encounters", "location_name", "TEXT")
    ensure_column("encounters", "location_area", "TEXT")
    ensure_column("encounters", "min_level", "INTEGER")
    ensure_column("encounters", "max_level", "INTEGER")
    ensure_column("encounters", "method", "TEXT")
    ensure_column("pokemon_moves", "pokemon", "TEXT")
    ensure_column("pokemon_moves", "move", "TEXT")
    ensure_column("pokemon_moves", "game", "TEXT")
    ensure_column("pokemon_moves", "method", "TEXT")
    ensure_column("pokemon_moves", "level", "INTEGER")
    ensure_column("gyms", "badge", "TEXT")
    ensure_column("evolutions", "held_item", "TEXT")
    ensure_column("evolutions", "item", "TEXT")
    ensure_column("evolutions", "min_happiness", "INTEGER")
    ensure_column("evolutions", "min_affection", "INTEGER")
    ensure_column("evolutions", "min_beauty", "INTEGER")
    ensure_column("evolutions", "known_move", "TEXT")
    ensure_column("evolutions", "known_move_type", "TEXT")
    ensure_column("evolutions", "location", "TEXT")
    ensure_column("evolutions", "trade_species", "TEXT")
    ensure_column("evolutions", "party_species", "TEXT")
    ensure_column("evolutions", "party_type", "TEXT")
    ensure_column("evolutions", "relative_physical_stats", "INTEGER")
    ensure_column("evolutions", "time_of_day", "TEXT")
    ensure_column("evolutions", "needs_overworld_rain", "INTEGER")
    ensure_column("evolutions", "turn_upside_down", "INTEGER")
    # gym_teams table is created by schema; nothing else to ensure here


if __name__ == "__main__":
    migrate()
    print(f"Initialized database at {DB_PATH}")
