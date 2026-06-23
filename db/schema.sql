CREATE TABLE IF NOT EXISTS abilities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    generation TEXT,
    short_effect TEXT,
    effect TEXT
);
CREATE INDEX IF NOT EXISTS idx_abilities_name ON abilities(name);

CREATE TABLE IF NOT EXISTS pokemon (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    pokedex_number INTEGER,
    generation TEXT,
    type1 TEXT,
    type2 TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER,
    sp_attack INTEGER,
    sp_defense INTEGER,
    speed INTEGER,
    ability_1 TEXT,
    ability_2 TEXT,
    hidden_ability TEXT,
    base_experience INTEGER,
    height INTEGER,
    weight INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pokemon_name ON pokemon(name);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    type TEXT,
    category TEXT,
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER,
    generation TEXT,
    effect TEXT
);
CREATE INDEX IF NOT EXISTS idx_moves_name ON moves(name);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    category TEXT,
    cost INTEGER,
    fling_power INTEGER,
    fling_effect TEXT,
    generation TEXT,
    short_effect TEXT,
    effect TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);

CREATE TABLE IF NOT EXISTS apricorn_recipes (
    id INTEGER PRIMARY KEY,
    game TEXT,
    item TEXT,
    ingredient TEXT,
    quantity INTEGER,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_apricorn_recipes_item ON apricorn_recipes(item);
CREATE INDEX IF NOT EXISTS idx_apricorn_recipes_game_item ON apricorn_recipes(game, item);

CREATE TABLE IF NOT EXISTS egg_groups (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_egg_groups_name ON egg_groups(name);

CREATE TABLE IF NOT EXISTS pokemon_egg_groups (
    id INTEGER PRIMARY KEY,
    pokemon TEXT,
    egg_group TEXT
);
CREATE INDEX IF NOT EXISTS idx_pokemon_egg_groups_pokemon ON pokemon_egg_groups(pokemon);
CREATE INDEX IF NOT EXISTS idx_pokemon_egg_groups_egg_group ON pokemon_egg_groups(egg_group);

CREATE TABLE IF NOT EXISTS pokemon_breeding (
    id INTEGER PRIMARY KEY,
    pokemon TEXT UNIQUE,
    gender_rate INTEGER,
    egg_cycles INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pokemon_breeding_pokemon ON pokemon_breeding(pokemon);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    region TEXT
);
CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);

CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY,
    game TEXT,
    route TEXT,
    location_name TEXT,
    location_area TEXT,
    pokemon TEXT,
    min_level INTEGER,
    max_level INTEGER,
    chance INTEGER,
    method TEXT
);
CREATE INDEX IF NOT EXISTS idx_encounters_route ON encounters(route);
CREATE INDEX IF NOT EXISTS idx_encounters_location ON encounters(location_name);
CREATE INDEX IF NOT EXISTS idx_encounters_game ON encounters(game);

CREATE TABLE IF NOT EXISTS gyms (
    id INTEGER PRIMARY KEY,
    game TEXT,
    gym_number INTEGER,
    leader TEXT,
    city TEXT,
    type TEXT,
    badge TEXT
);
CREATE INDEX IF NOT EXISTS idx_gyms_game ON gyms(game);

CREATE TABLE IF NOT EXISTS gym_teams (
    id INTEGER PRIMARY KEY,
    game TEXT,
    gym_number INTEGER,
    pokemon TEXT,
    position INTEGER
);
CREATE INDEX IF NOT EXISTS idx_gym_teams_game_gym ON gym_teams(game, gym_number);

CREATE TABLE IF NOT EXISTS tms (
    id INTEGER PRIMARY KEY,
    game TEXT,
    code TEXT,
    move TEXT
);
CREATE INDEX IF NOT EXISTS idx_tms_game_code ON tms(game, code);

CREATE TABLE IF NOT EXISTS pokemon_moves (
    id INTEGER PRIMARY KEY,
    pokemon TEXT,
    move TEXT,
    game TEXT,
    method TEXT,
    level INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pokemon_moves_pokemon_game ON pokemon_moves(pokemon, game);
CREATE INDEX IF NOT EXISTS idx_pokemon_moves_move_game ON pokemon_moves(move, game);

CREATE TABLE IF NOT EXISTS evolutions (
    id INTEGER PRIMARY KEY,
    pokemon TEXT,
    evolves_to TEXT,
    method TEXT,
    min_level INTEGER,
    item TEXT,
    held_item TEXT,
    min_happiness INTEGER,
    min_affection INTEGER,
    min_beauty INTEGER,
    known_move TEXT,
    known_move_type TEXT,
    location TEXT,
    trade_species TEXT,
    party_species TEXT,
    party_type TEXT,
    relative_physical_stats INTEGER,
    time_of_day TEXT,
    needs_overworld_rain INTEGER,
    turn_upside_down INTEGER
);
CREATE INDEX IF NOT EXISTS idx_evolutions_pokemon ON evolutions(pokemon);
