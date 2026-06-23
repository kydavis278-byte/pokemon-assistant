import re
import sqlite3
import difflib

from core.router import parse
from core.db import fetch_one, fetch_all
from core.formatter import format_response, _normalize_move_name, _move_label_line


EGG_GROUP_ALIASES = {
    "normal": "monster",
    "monster": "monster",
    "human shape": "humanshape",
    "human-shaped": "humanshape",
    "humanshape": "humanshape",
    "humanlike": "humanshape",
    "humanshape": "humanshape",
    "water 1": "water1",
    "water1": "water1",
    "water 2": "water2",
    "water2": "water2",
    "water 3": "water3",
    "water3": "water3",
    "no eggs": "no-eggs",
    "no-eggs": "no-eggs",
}


def _normalize_egg_group_name(group_name):
    if not group_name:
        return group_name
    normalized = group_name.lower().strip()
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = EGG_GROUP_ALIASES.get(normalized, normalized.replace(" ", ""))
    return normalized


def _safe_row_value(row, key, default=None):
    try:
        value = row[key]
    except Exception:
        value = None
    return value if value is not None else default


SPECIAL_TRADE_ITEM_FALLBACKS = {
    ("slowpoke", "slowking"): "King's Rock",
    ("poliwhirl", "politoed"): "King's Rock",
    ("seadra", "kingdra"): "Dragon Scale",
    ("clamperl", "huntail"): "Deep Sea Tooth",
    ("clamperl", "gorebyss"): "Deep Sea Scale",
}

FORM_ALIASES = {
    "mega": "mega",
    "alolan": "alola",
    "galarian": "galar",
    "hisuian": "hisui",
    "paldean": "paldea",
}

FORM_DISPLAY_NAMES = {
    "mega": "Mega",
    "alola": "Alolan",
    "galar": "Galarian",
    "hisui": "Hisui",
    "paldea": "Paldean",
}

POKEMON_TYPES = {
    "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
    "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy",
}

GAME_ORDER = [
    "red", "blue", "yellow", "green",
    "gold", "silver", "crystal",
    "ruby", "sapphire", "emerald", "firered", "leafgreen",
    "diamond", "pearl", "platinum", "heart gold", "soul silver",
    "black", "white", "black 2", "white 2",
    "x", "y", "omega ruby", "alpha sapphire",
    "sun", "moon", "ultra sun", "ultra moon",
    "sword", "shield", "brilliant diamond", "shining pearl",
    "legends arceus", "scarlet", "violet",
]

GAME_RANK = {name: idx for idx, name in enumerate(GAME_ORDER)}

GENERATION_GAMES = {
    "generation i": ["red", "blue", "yellow", "green"],
    "generation ii": ["gold", "silver", "crystal"],
    "generation iii": ["ruby", "sapphire", "emerald", "firered", "leafgreen"],
    "generation iv": ["diamond", "pearl", "platinum", "heart gold", "soul silver"],
    "generation v": ["black", "white", "black 2", "white 2"],
    "generation vi": ["x", "y", "omega ruby", "alpha sapphire"],
    "generation vii": ["sun", "moon", "ultra sun", "ultra moon", "let's go pikachu", "let's go eevee"],
    "generation viii": ["sword", "shield", "brilliant diamond", "shining pearl", "legends arceus"],
    "generation ix": ["scarlet", "violet"],
}


def _normalize_game_key(value):
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value.replace("-", " ").strip().lower())
    compact = cleaned.replace(" ", "")
    compact_aliases = {
        "firered": "firered",
        "leafgreen": "leafgreen",
        "heartgold": "heart gold",
        "soulsilver": "soul silver",
        "black2": "black 2",
        "white2": "white 2",
        "omegaruby": "omega ruby",
        "alphasapphire": "alpha sapphire",
        "ultrasun": "ultra sun",
        "ultramoon": "ultra moon",
        "brilliantdiamond": "brilliant diamond",
        "shiningpearl": "shining pearl",
        "legendsarceus": "legends arceus",
    }
    return compact_aliases.get(compact, cleaned)


def _game_rank(value):
    key = _normalize_game_key(value)
    return GAME_RANK.get(key, -1)


def _display_game_name(value):
    if not value:
        return "Unknown"
    compact = value.lower().replace(' ', '').replace('-', '')
    display_overrides = {
        "firered": "Fire Red",
        "leafgreen": "Leaf Green",
        "heartgold": "Heart Gold",
        "soulsilver": "Soul Silver",
        "omegaruby": "Omega Ruby",
        "alphasapphire": "Alpha Sapphire",
        "ultrasun": "Ultra Sun",
        "ultramoon": "Ultra Moon",
    }
    if compact in display_overrides:
        return display_overrides[compact]
    return (value or "Unknown").replace('-', ' ').title()


def _format_learn_level(value, method=None):
    if method and method.lower() != "level-up":
        return "-"
    if value is None:
        return "-"
    return str(value)


def _format_egg_group_label(value):
    label = (value or '').replace('-', ' ').title()
    return re.sub(r"([A-Za-z])(\d)", r"\1 \2", label)


def _fetch_egg_group_members(group_name, game=None, generation=None):
    query = """
        SELECT DISTINCT p.name AS pokemon, COALESCE(p.pokedex_number, p.id, 99999) AS order_key
        FROM pokemon_egg_groups peg
        JOIN pokemon p ON lower(p.name)=lower(peg.pokemon)
        WHERE lower(peg.egg_group)=?
    """
    params = [group_name.lower()]

    if game:
        game_key = game.lower()
        game_plain = game_key.replace(' ', '')
        game_hyphen = game_key.replace(' ', '-')
        query += """
            AND lower(peg.pokemon) IN (
                SELECT DISTINCT lower(pm.pokemon)
                FROM pokemon_moves pm
                WHERE lower(pm.game)=? OR lower(pm.game)=? OR lower(pm.game)=?
                   OR lower(pm.game) LIKE ? OR lower(pm.game) LIKE ?
            )
        """
        params.extend([game_key, game_plain, game_hyphen, f"%{game_plain}%", f"%{game_hyphen}%"])
    elif generation:
        gen_games = GENERATION_GAMES.get(generation.lower(), [])
        if gen_games:
            placeholders = ",".join(["?"] * len(gen_games))
            query += f"""
                AND lower(peg.pokemon) IN (
                    SELECT DISTINCT lower(pm.pokemon)
                    FROM pokemon_moves pm
                    WHERE lower(pm.game) IN ({placeholders})
                )
            """
            params.extend([g.lower() for g in gen_games])

    query += " ORDER BY order_key, pokemon"
    return fetch_all(query, tuple(params))


def _format_egg_group_member_lines(rows):
    if not rows:
        return []

    members = []
    by_name = {}
    for r in rows:
        name = (r['pokemon'] or '').strip()
        if not name:
            continue
        key = name.lower()
        dex = r['order_key'] if r['order_key'] is not None else 99999
        entry = {'key': key, 'name': name.title(), 'dex': int(dex)}
        members.append(entry)
        by_name[key] = entry

    if not members:
        return []

    keys = [m['key'] for m in members]
    placeholders = ",".join(["?"] * len(keys))
    edges = fetch_all(
        f"""
            SELECT lower(pokemon) AS a, lower(evolves_to) AS b
            FROM evolutions
            WHERE lower(pokemon) IN ({placeholders})
               OR lower(evolves_to) IN ({placeholders})
        """,
        tuple(keys + keys),
    )

    parent = {k: k for k in keys}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for e in edges:
        a = (e['a'] or '').strip()
        b = (e['b'] or '').strip()
        if not a or not b:
            continue
        if a in parent and b in parent:
            union(a, b)

    groups = {}
    for m in members:
        root = find(m['key'])
        groups.setdefault(root, []).append(m)

    lines_data = []
    for comp in groups.values():
        comp.sort(key=lambda x: (x['dex'], x['name']))
        line = ", ".join([x['name'] for x in comp])
        lines_data.append((comp[0]['dex'], line))

    lines_data.sort(key=lambda x: x[0])
    return [line for _, line in lines_data]


def _resolve_species_name_for_breeding(pokemon_query):
    if not pokemon_query:
        return None

    pokemon_row = _find_by_name("pokemon", pokemon_query)
    candidate = (pokemon_row['name'] if pokemon_row and pokemon_row['name'] else pokemon_query).lower().strip()
    candidate = _canonical_evolution_name(candidate)

    # Handle casual possessive/plural forms from user input (e.g., "magbys").
    if candidate.endswith("'s"):
        candidate = candidate[:-2].strip()
    elif candidate.endswith("s"):
        singular_try = candidate[:-1].strip()
        row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (singular_try,))
        if row:
            candidate = singular_try

    checks = []
    checks.append(candidate)
    parts = candidate.split()
    for i in range(len(parts) - 1, 0, -1):
        checks.append(" ".join(parts[:i]))

    seen = set()
    for check in checks:
        if not check or check in seen:
            continue
        seen.add(check)
        row = fetch_one("SELECT pokemon FROM pokemon_breeding WHERE lower(pokemon)=?", (check,))
        if row and row['pokemon']:
            return row['pokemon']

    row = fetch_one("SELECT pokemon FROM pokemon_breeding WHERE lower(pokemon) LIKE ? ORDER BY length(pokemon) ASC LIMIT 1", (f"%{candidate}%",))
    if row and row['pokemon']:
        return row['pokemon']

    # Last-chance typo tolerance for close spellings (e.g., vullabay -> vullaby).
    all_species = fetch_all("SELECT pokemon FROM pokemon_breeding")
    names = [r['pokemon'] for r in all_species if r and r['pokemon']]
    close = difflib.get_close_matches(candidate, names, n=1, cutoff=0.82)
    return close[0] if close else None


def _select_latest_game_for_species_breeding(species_name):
    rows = fetch_all(
        "SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE lower(pokemon)=? OR lower(pokemon) LIKE ? GROUP BY game",
        (species_name.lower(), f"{species_name.lower()} %"),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def _select_latest_game_for_species_breeding_in_generation(species_name, generation):
    gen_games = GENERATION_GAMES.get((generation or "").lower(), [])
    if not gen_games:
        return None
    placeholders = ",".join(["?"] * len(gen_games))
    rows = fetch_all(
        f"SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE (lower(pokemon)=? OR lower(pokemon) LIKE ?) AND lower(game) IN ({placeholders}) GROUP BY game",
        tuple([species_name.lower(), f"{species_name.lower()} %", *[g.lower() for g in gen_games]]),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def _get_breeding_values(species_name):
    row = fetch_one("SELECT * FROM pokemon_breeding WHERE lower(pokemon)=?", (species_name.lower(),))
    if not row:
        return None
    groups = fetch_all(
        "SELECT egg_group FROM pokemon_egg_groups WHERE lower(pokemon)=? ORDER BY egg_group",
        (species_name.lower(),),
    )
    egg_groups = []
    for g in groups:
        if not g or not g['egg_group']:
            continue
        label = _format_egg_group_label(g['egg_group'])
        egg_groups.append(label)

    gender_rate = row['gender_rate']
    if gender_rate is None or int(gender_rate) < 0:
        gender_text = "Genderless"
    else:
        female_pct = round((int(gender_rate) / 8.0) * 100, 1)
        male_pct = round(100 - female_pct, 1)
        gender_text = f"Male {male_pct}% | Female {female_pct}%"

    cycles = row['egg_cycles']
    steps = int(cycles) * 255 if cycles is not None else None
    return {
        "egg_groups": egg_groups,
        "gender_text": gender_text,
        "egg_cycles": cycles,
        "egg_steps": steps,
    }


def _format_egg_cycles_line(cycles):
    if cycles is None:
        return "Egg Cycles: Unknown"
    max_steps = int(cycles) * 257
    min_steps = max_steps - 256
    return f"Egg Cycles: {cycles} ({min_steps:,}-{max_steps:,} steps)"


def handle_breeding(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a pokemon name, for example: give me breeding info on mudkip.", None

    pokemon_query = (entity.get('pokemon') or '').strip()
    game = (entity.get('game') or '').strip() or None
    generation = (entity.get('generation') or '').strip() or None
    field = (entity.get('field') or 'all').strip().lower()

    if not pokemon_query:
        return "Please include a pokemon name for breeding info.", None

    species_name = _resolve_species_name_for_breeding(pokemon_query)
    if not species_name:
        return "Pokémon not found.", None

    data = _get_breeding_values(species_name)
    if not data:
        return f"No breeding data found for {species_name.title()}.", None

    source_game = game or _select_latest_game_for_species_breeding_in_generation(species_name, generation) or _select_latest_game_for_species_breeding(species_name)
    source_label = _display_game_name(source_game) if source_game else (generation.title() if generation else "Latest")
    prefix = f"{species_name.title()} breeding data ({source_label}):"

    if field == "egg_groups":
        groups = ", ".join(data['egg_groups']) if data['egg_groups'] else "Unknown"
        return f"Egg groups for {species_name.title()} ({source_label}): {groups}", None

    if field == "gender":
        return f"Gender rate for {species_name.title()} ({source_label}): {data['gender_text']}", None

    if field == "cycles":
        return f"{species_name.title()} breeding data ({source_label}):\n{_format_egg_cycles_line(data['egg_cycles'])}", None

    if field == "steps":
        return f"{species_name.title()} breeding data ({source_label}):\n{_format_egg_cycles_line(data['egg_cycles'])}", None

    groups = ", ".join(data['egg_groups']) if data['egg_groups'] else "Unknown"
    lines = [
        prefix,
        f"Egg Groups: {groups}",
        f"Gender Rate: {data['gender_text']}",
        _format_egg_cycles_line(data['egg_cycles']),
    ]
    return "\n".join(lines), None


def _pokemon_form_hint(entity_name):
    if not entity_name:
        return None
    cleaned = re.sub(r"\s+", " ", entity_name.replace("-", " ").strip().lower())
    parts = cleaned.split()
    if not parts:
        return None
    return FORM_ALIASES.get(parts[0])


def _pokemon_base_name(name):
    if not name:
        return None
    cleaned = re.sub(r"\s+", " ", name.replace("-", " ").strip().lower())
    parts = cleaned.split()
    if len(parts) >= 2 and parts[-1] in FORM_DISPLAY_NAMES:
        return " ".join(parts[:-1])
    return cleaned


def _canonical_evolution_name(name):
    if not name:
        return name
    cleaned = re.sub(r"\s+", " ", name.replace("-", " ").strip().lower())
    if cleaned.endswith(" gmax"):
        return cleaned[:-5]

    # Many form names are stored in pokemon, but evolutions are keyed by base species.
    # Trim trailing form tokens until we reach a species name referenced in evolutions.
    candidate = cleaned
    while candidate and ' ' in candidate:
        row = fetch_one(
            "SELECT 1 FROM evolutions WHERE lower(pokemon)=? OR lower(evolves_to)=? LIMIT 1",
            (candidate, candidate),
        )
        if row:
            return candidate
        candidate = candidate.rsplit(' ', 1)[0]

    row = fetch_one(
        "SELECT 1 FROM evolutions WHERE lower(pokemon)=? OR lower(evolves_to)=? LIMIT 1",
        (candidate, candidate),
    )
    if row:
        return candidate
    return cleaned


def _special_form_outcomes(source_name, child_rows, region_hint=None, query_name=None):
    if not source_name or not child_rows:
        return None

    source = source_name.lower().strip()
    targets = {(_safe_row_value(r, 'evolves_to') or '').lower() for r in child_rows}
    targets.discard('')
    if not targets:
        return None

    # Toxel has one generic chain row but two deterministic forms.
    if source == "toxel" and targets == {"toxtricity"}:
        return [
            "(Level 30, Amped Nature)",
            "Toxtricity Amped",
            "(Level 30, Low Key Nature)",
            "Toxtricity Low Key",
        ]

    # Rockruff rows differ by time_of_day but all target generic Lycanroc.
    if source == "rockruff" and targets == {"lycanroc"}:
        form_map = {
            'day': 'Lycanroc Midday',
            'night': 'Lycanroc Midnight',
            'dusk': 'Lycanroc Dusk',
        }
        order = ['day', 'night', 'dusk']
        lines = []
        seen = set()
        by_tod = {(_safe_row_value(r, 'time_of_day') or '').lower(): r for r in child_rows}
        for tod in order:
            row = by_tod.get(tod)
            if not row:
                continue
            requirement = _format_evolution_requirement(row, region_hint=region_hint)
            if requirement:
                lines.append(f"({requirement})")
            display = form_map[tod]
            if display not in seen:
                lines.append(display)
                seen.add(display)
        if lines:
            return lines

    # Kubfu has generic Urshifu target with split outcomes by tower/scroll.
    if source == "kubfu" and targets == {"urshifu"}:
        lines = []
        forms = {
            'single strike': None,
            'rapid strike': None,
        }
        for row in child_rows:
            method = (_safe_row_value(row, 'method') or '').lower()
            item = (_safe_row_value(row, 'item') or '').lower()
            key = None
            if 'darkness' in method or 'darkness' in item:
                key = 'single strike'
            elif 'waters' in method or 'water' in method or 'waters' in item or 'water' in item:
                key = 'rapid strike'
            if key and forms[key] is None:
                forms[key] = row
        for key, display in [('single strike', 'Urshifu Single Strike'), ('rapid strike', 'Urshifu Rapid Strike')]:
            row = forms.get(key)
            if not row:
                continue
            requirement = _format_evolution_requirement(row, region_hint=region_hint)
            if requirement:
                lines.append(f"({requirement})")
            lines.append(display)
        if lines:
            return lines

    # Pumpkaboo size form evolves into matching Gourgeist size form.
    if source.startswith("pumpkaboo") and targets == {"gourgeist"}:
        q = (query_name or source_name or '').lower()
        sizes = ['small', 'average', 'large', 'super']
        size = next((s for s in sizes if re.search(rf"\b{s}\b", q)), None)
        if size:
            row = child_rows[0]
            lines = []
            requirement = _format_evolution_requirement(row, region_hint=region_hint)
            if requirement:
                lines.append(f"({requirement})")
            lines.append(f"Gourgeist {size.title()}")
            return lines

    # Espurr and Lechonk split into male/female forms, but chain rows are generic.
    if source == "espurr" and targets == {"meowstic"}:
        row = child_rows[0]
        requirement = _format_evolution_requirement(row, region_hint=region_hint) or "Level 25"
        return [
            f"({requirement}, Male)",
            "Meowstic Male",
            f"({requirement}, Female)",
            "Meowstic Female",
        ]

    if source == "lechonk" and targets == {"oinkologne"}:
        row = child_rows[0]
        requirement = _format_evolution_requirement(row, region_hint=region_hint) or "Level 18"
        return [
            f"({requirement}, Male)",
            "Oinkologne Male",
            f"({requirement}, Female)",
            "Oinkologne Female",
        ]

    if source.startswith("basculin") and targets == {"basculegion"}:
        row = child_rows[0]
        requirement = _format_evolution_requirement(row, region_hint=region_hint)
        lines = []
        if requirement:
            lines.append(f"({requirement}, Male)")
        lines.append("Basculegion Male")
        if requirement:
            lines.append(f"({requirement}, Female)")
        lines.append("Basculegion Female")
        return lines

    return None


def _pokemon_form_variant_name(base_name, form_hint):
    if not base_name or not form_hint:
        return None
    candidate = f"{base_name} {form_hint}"
    row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (candidate,))
    return row['name'] if row and row['name'] else None


def _pokemon_display_name(name, form_hint=None):
    if not name:
        return None
    base_name = _pokemon_base_name(name)
    if not base_name:
        return name.title()

    suffix_form = None
    parts = base_name.split()
    if len(parts) >= 2 and parts[-1] in FORM_DISPLAY_NAMES:
        suffix_form = parts[-1]
        base_name = " ".join(parts[:-1])

    display_form = FORM_DISPLAY_NAMES.get(form_hint or suffix_form)
    variant_name = _pokemon_form_variant_name(base_name, form_hint or suffix_form)
    if display_form and base_name and variant_name:
        return f"{display_form} {base_name.title()}"
    return base_name.title() if base_name else name.title()


def _find_by_name(table, entity_name):
    if not entity_name:
        return None

    def _normalize_spaces(value):
        return re.sub(r"\s+", " ", value.strip().lower())

    def _entity_variants(value):
        # PokeAPI form names are often stored as "<pokemon> <form>" (e.g. "swampert mega"),
        # while users may ask with the form first (e.g. "mega swampert").
        cleaned = _normalize_spaces(value.replace("-", " "))
        variants = []
        seen = set()

        def add_variant(v):
            key = (v or "").strip()
            if not key or key in seen:
                return
            seen.add(key)
            variants.append(key)

        add_variant(cleaned)
        parts = cleaned.split()
        if table == "pokemon" and len(parts) >= 2:
            form_prefixes = {
                "mega": "mega",
                "alolan": "alola",
                "galarian": "galar",
                "hisuian": "hisui",
                "paldean": "paldea",
            }
            first = parts[0]
            if first in form_prefixes:
                add_variant(" ".join(parts[1:] + [form_prefixes[first]]))

        if table == "moves" and len(parts) >= 2:
            # Flexible G-Max aliases, while preserving exact matches first:
            # "g fireball", "gmax fireball", "g max fireball", "max fireball".
            if parts[0] == "g" and len(parts) >= 3 and parts[1] == "max":
                tail = " ".join(parts[2:])
                add_variant(f"max {tail}")
                add_variant(f"g max {tail}")
                add_variant(f"g-max {tail}")
            elif parts[0] == "g" and len(parts) >= 2:
                tail = " ".join(parts[1:])
                add_variant(f"max {tail}")
                add_variant(f"g max {tail}")
                add_variant(f"g-max {tail}")
            elif parts[0] == "gmax" and len(parts) >= 2:
                tail = " ".join(parts[1:])
                add_variant(f"max {tail}")
                add_variant(f"g max {tail}")
                add_variant(f"g-max {tail}")
            elif parts[0] == "max" and len(parts) >= 2:
                # Keep plain max form first, then try g-max fallback.
                tail = " ".join(parts[1:])
                add_variant(f"g max {tail}")
                add_variant(f"g-max {tail}")

        return variants

    candidates = _entity_variants(entity_name)

    for candidate in candidates:
        row = fetch_one(
            f"SELECT * FROM {table} WHERE lower(name)=?",
            (candidate,)
        )
        if row:
            return row

    for candidate in candidates:
        row = fetch_one(
            f"SELECT * FROM {table} WHERE lower(name) LIKE ? ORDER BY length(name) ASC LIMIT 1",
            (f"%{candidate}%",)
        )
        if row:
            return row

    # Last-pass robust matching: ignore spaces/hyphens so entries like
    # "acid downpour  physical" still match "acid downpour physical".
    for candidate in candidates:
        compact = re.sub(r"[\s-]+", "", candidate)
        if not compact:
            continue
        row = fetch_one(
            f"SELECT * FROM {table} WHERE replace(replace(lower(name), ' ', ''), '-', '')=? LIMIT 1",
            (compact,),
        )
        if row:
            return row

    return None


def _find_exact_by_name(table, entity_name):
    if not entity_name:
        return None
    return fetch_one(
        f"SELECT * FROM {table} WHERE lower(name)=?",
        (entity_name.lower(),)
    )


def _route_matches(route_value, requested_route):
    if not route_value or requested_route is None:
        return False
    route_text = str(route_value).strip().lower()
    route_token = str(requested_route).strip().lower()
    # Match route numbers/tokens exactly (e.g. route 1, route 201, route 7a)
    # so route 1 does not incorrectly include route 10-19.
    return re.search(rf"\broute\s*{re.escape(route_token)}\b", route_text) is not None


def _format_encounter_method(method_value):
    if not method_value:
        return "Unknown"
    text = method_value.replace('-', ' ').strip().lower()
    if text == 'npc' or text.startswith('npc '):
        return text.upper()
    return re.sub(r"\s+", " ", text).title()


def _build_evolution_tree(pokemon_name, entity_name=None):
    if not pokemon_name:
        return None

    current = pokemon_name.strip().lower()
    if not current:
        return None

    form_hint = _pokemon_form_hint(entity_name) or _pokemon_form_hint(pokemon_name)
    region_hint = "In Legends Arceus" if form_hint == "hisui" else None
    target_name = _canonical_evolution_name(_pokemon_base_name(current) or current)

    # Walk backward to the base form.
    seen = set()
    root = target_name
    while root not in seen:
        seen.add(root)
        prev_rows = fetch_all(
            "SELECT * FROM evolutions WHERE lower(evolves_to)=? ORDER BY min_level IS NULL, min_level",
            (root,),
        )
        if not prev_rows:
            break
        root = _pokemon_base_name(prev_rows[0]['pokemon'].lower()) or prev_rows[0]['pokemon'].lower()

    path = _find_evolution_path(root, target_name)
    if not path:
        return None

    lines = ["Evolution Tree:"]
    for stage_name, evolution_row in path:
        row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (stage_name,))
        source_name = row['name'] if row and row['name'] else stage_name
        if stage_name == target_name and current != target_name:
            query_row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (current,))
            if query_row and query_row['name']:
                source_name = query_row['name']
        display_name = _pokemon_display_name(source_name, form_hint=form_hint)
        lines.append(display_name)
        if evolution_row:
            requirement = _format_evolution_requirement(evolution_row, region_hint=region_hint)
            if requirement:
                lines.append(f"({requirement})")

    # If the queried Pokémon is a branching point (like Eevee), expand all branches.
    # Otherwise if it's a middle stage, continue down one branch (e.g. Mudkip -> Marshtomp -> Swampert).
    tail = target_name
    children = fetch_all(
        "SELECT * FROM evolutions WHERE lower(pokemon)=? ORDER BY evolves_to, min_level IS NULL, min_level",
        (tail,),
    )
    if children:
        special_lines = _special_form_outcomes(tail, children, region_hint=region_hint, query_name=current)
        if special_lines:
            lines.extend(special_lines)
            return "\n".join(lines)

        seen_evolves = set()
        for child in children:
            next_name = (_safe_row_value(child, 'evolves_to') or '').lower()
            if next_name and next_name not in seen_evolves:
                seen_evolves.add(next_name)

        if len(seen_evolves) > 1:
            # Branching node: expand all branches
            branch_lines = _expand_all_branches(tail, form_hint=form_hint, region_hint=region_hint)
            lines.extend(branch_lines)
        else:
            # Linear chain: continue as before
            next_row = children[0] if children else None
            if next_row:
                next_name = (_safe_row_value(next_row, 'evolves_to') or '').lower()
                requirement = _format_evolution_requirement(next_row, region_hint=region_hint)
                if requirement:
                    lines.append(f"({requirement})")
                if next_name:
                    row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (next_name,))
                    source_name = row['name'] if row and row['name'] else next_name
                    display_name = _pokemon_display_name(source_name, form_hint=form_hint)
                    lines.append(display_name)
                    seen = {stage_name for stage_name, _ in path}
                    seen.add(next_name)
                    tail = next_name
                    while True:
                        children = fetch_all(
                            "SELECT * FROM evolutions WHERE lower(pokemon)=? ORDER BY min_level IS NULL, min_level",
                            (tail,),
                        )
                        if not children:
                            break
                        next_row = None
                        for child in children:
                            next_name = (_safe_row_value(child, 'evolves_to') or '').lower()
                            if next_name and next_name not in seen:
                                next_row = child
                                break
                        if not next_row:
                            break
                        requirement = _format_evolution_requirement(next_row, region_hint=region_hint)
                        if requirement:
                            lines.append(f"({requirement})")
                        next_name = (_safe_row_value(next_row, 'evolves_to') or '').lower()
                        if not next_name:
                            break
                        row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (next_name,))
                        source_name = row['name'] if row and row['name'] else next_name
                        display_name = _pokemon_display_name(source_name, form_hint=form_hint)
                        lines.append(display_name)
                        seen.add(next_name)
                        tail = next_name
    return "\n".join(lines)


def _expand_all_branches(node, form_hint=None, region_hint=None, max_depth=10):
    """Recursively expand all evolution branches from a given node."""
    if max_depth <= 0 or not node:
        return []

    children = fetch_all(
        "SELECT * FROM evolutions WHERE lower(pokemon)=? ORDER BY evolves_to, min_level IS NULL, min_level",
        (node,),
    )
    if not children:
        return []

    special_lines = _special_form_outcomes(node, children, region_hint=region_hint, query_name=node)
    if special_lines:
        return special_lines

    lines = []
    seen_branches = set()
    for child in children:
        next_name = (_safe_row_value(child, 'evolves_to') or '').lower()
        if not next_name or next_name in seen_branches:
            continue

        seen_branches.add(next_name)

        requirement = _format_evolution_requirement(child, region_hint=region_hint)
        if requirement:
            lines.append(f"({requirement})")

        row = fetch_one("SELECT name FROM pokemon WHERE lower(name)=?", (next_name,))
        source_name = row['name'] if row and row['name'] else next_name
        display_name = _pokemon_display_name(source_name, form_hint=form_hint)
        lines.append(display_name)

        sub_branches = _expand_all_branches(next_name, form_hint=form_hint, region_hint=region_hint, max_depth=max_depth-1)
        if sub_branches:
            lines.extend(sub_branches)

    return lines


def _find_evolution_path(node, target, visited=None):
    if not node:
        return None
    if visited is None:
        visited = set()
    if node in visited:
        return None
    visited = set(visited)
    visited.add(node)

    if node == target:
        return [(node, None)]

    children = fetch_all(
        "SELECT * FROM evolutions WHERE lower(pokemon)=? ORDER BY min_level IS NULL, min_level",
        (node,),
    )
    for child in children:
        next_node = (_safe_row_value(child, 'evolves_to') or '').lower()
        if not next_node:
            continue
        path = _find_evolution_path(next_node, target, visited)
        if path:
            return [(node, child)] + path
    return None


def _format_evolution_requirement(row, region_hint=None):
    if not row:
        return None

    method = (_safe_row_value(row, 'method') or '').replace('-', ' ').strip().lower()
    min_level = _safe_row_value(row, 'min_level')
    item_value = _safe_row_value(row, 'item')
    held_item_value = _safe_row_value(row, 'held_item')
    known_move_value = _safe_row_value(row, 'known_move')
    known_move_type_value = _safe_row_value(row, 'known_move_type')
    location_value = _safe_row_value(row, 'location')
    trade_species_value = _safe_row_value(row, 'trade_species')
    party_species_value = _safe_row_value(row, 'party_species')
    party_type_value = _safe_row_value(row, 'party_type')
    time_of_day_value = _safe_row_value(row, 'time_of_day')

    item = item_value.replace('-', ' ').strip().title() if item_value else None
    held_item = held_item_value.replace('-', ' ').strip().title() if held_item_value else None
    known_move = known_move_value.replace('-', ' ').strip().title() if known_move_value else None
    known_move_type = known_move_type_value.replace('-', ' ').strip().title() if known_move_type_value else None
    location = location_value.replace('-', ' ').strip().title() if location_value else None
    trade_species = trade_species_value.replace('-', ' ').strip().title() if trade_species_value else None
    party_species = party_species_value.replace('-', ' ').strip().title() if party_species_value else None
    party_type = party_type_value.replace('-', ' ').strip().title() if party_type_value else None
    time_of_day = time_of_day_value.replace('-', ' ').strip().lower() if time_of_day_value else None

    if min_level is not None:
        text = f"Level {min_level}"
        if time_of_day in {"day", "night", "morning", "dusk"}:
            text = f"{text} at {time_of_day}"
        if region_hint:
            text = f"{text} {region_hint}"
        return text

    if method == 'trade' and not held_item and not item:
        fallback_item = SPECIAL_TRADE_ITEM_FALLBACKS.get((str(_safe_row_value(row, 'pokemon') or '').lower(), str(_safe_row_value(row, 'evolves_to') or '').lower()))
        if fallback_item:
            held_item = fallback_item

    parts = []
    if method == 'trade':
        if held_item:
            parts.append(f"Trade with {held_item}")
        elif item:
            parts.append(f"Trade with {item}")
        else:
            parts.append("Trade")
        if trade_species:
            parts.append(f"for {trade_species}")
    elif method == 'use item':
        parts.append(f"Use {item or held_item}" if (item or held_item) else "Use item")
    elif method == 'level up':
        parts.append("Level up")
    elif method:
        parts.append(method.replace(' ', ' ').title())

    if _safe_row_value(row, 'min_happiness') is not None:
        parts.append("with high friendship")
    if _safe_row_value(row, 'min_affection') is not None:
        parts.append("with high affection")
    if _safe_row_value(row, 'min_beauty') is not None:
        parts.append("with high beauty")
    if known_move:
        parts.append(f"knowing {known_move}")
    if known_move_type:
        parts.append(f"knowing a {known_move_type} move")
    if location:
        parts.append(f"at {location}")
    if party_species:
        parts.append(f"with {party_species} in your party")
    if party_type:
        parts.append(f"with a {party_type} type in your party")

    rel = _safe_row_value(row, 'relative_physical_stats')
    if rel is not None:
        if rel > 0:
            parts.append("when Attack is higher than Defense")
        elif rel < 0:
            parts.append("when Defense is higher than Attack")
        else:
            parts.append("when Attack and Defense are equal")

    if time_of_day in {"day", "night", "morning", "dusk"}:
        parts.append(f"at {time_of_day}")
    if _safe_row_value(row, 'needs_overworld_rain'):
        parts.append("while it is raining")
    if _safe_row_value(row, 'turn_upside_down'):
        parts.append("while holding the system upside down")
    if region_hint:
        parts.append(region_hint)

    if not parts:
        return None

    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text[0].upper() + text[1:] if text else None


def _split_effect_text(effect):
    text = (effect or "").strip().replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "", "", None

    summary = text.split('. ')[0].strip()
    if summary and not summary.endswith('.'):
        summary += '.'
    remainder = text[len(summary):].strip()

    example = None
    example_match = None
    for phrase in [r"for example", r"for instance", r"e\.g\."]:
        match = re.search(rf"\b({phrase})\b", remainder, flags=re.IGNORECASE)
        if match and (example_match is None or match.start() < example_match.start()):
            example_match = match

    if example_match:
        example_start = example_match.start()
        example_text = remainder[example_start:]
        sentence_end = re.search(r"\.\s+|\.$", example_text)
        if sentence_end:
            example = example_text[: sentence_end.end()].strip()
        else:
            example = example_text.strip()
        remainder = remainder[:example_start].strip()

    if remainder.startswith('.'):
        remainder = remainder[1:].strip()

    return summary, remainder, example


def _effect_more_text(effect):
    raw = (effect or "").strip()
    if not raw:
        return ""

    # Keep original spacing/newlines from source text; remove only the first sentence.
    first_sentence = re.search(r"[.!?](?:\s|$)", raw)
    if not first_sentence:
        return raw
    remainder = raw[first_sentence.end():].lstrip()
    return remainder if remainder else raw


def _short_effect_summary(value):
    text = re.sub(r"\s+", " ", (value or "").replace("\n", " ")).strip()
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text


def _effect_summary(effect, fallback="No effect text."):
    summary, _, _ = _split_effect_text(effect)
    if summary:
        return summary
    text = re.sub(r"\s+", " ", (effect or "").replace("\n", " ")).strip()
    return text if text else fallback


def _count_sentences(text):
    cleaned = re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()
    if not cleaned:
        return 0
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return len([p for p in parts if re.search(r"[A-Za-z0-9]", p)])


def _make_followup_prompt(name, subject_type, summary, more, example):
    if example and more:
        prompt = f"{name}: {summary}\nWould you like an example or more details about this {subject_type}?"
    elif example:
        prompt = f"{name}: {summary}\nWould you like an example about this {subject_type}?"
    elif more:
        prompt = f"{name}: {summary}\nWould you like more details about this {subject_type}?"
    else:
        return None
    return prompt


def handle_ability_context(entity):
    row = _find_by_name("abilities", entity)
    if not row:
        return None, None

    effect = row['effect'] if row['effect'] is not None else row['short_effect'] if row['short_effect'] is not None else ''
    short_effect = _short_effect_summary(row['short_effect'] if row['short_effect'] is not None else '')
    name = row['name'].title() if row['name'] else 'Ability'
    summary, more, example = _split_effect_text(effect)
    more_text = _effect_more_text(effect)
    core_summary = short_effect or summary or _effect_summary(effect)
    sentence_count = _count_sentences(effect)

    if sentence_count >= 3 and (more_text or example):
        prompt = _make_followup_prompt(name, 'ability', core_summary, more, example)
        if prompt:
            return prompt, {
                'type': 'followup',
                'category': 'ability',
                'name': name,
                'more': more_text,
                'example': example,
            }

    return f"{name}: {core_summary}", None


def handle_move_context(entity):
    row = _find_by_name("moves", entity)
    if not row:
        return None, None

    effect = row['effect'] or ''
    name = _normalize_move_name(row['name']).title() if row['name'] else 'Move'
    move_label = _move_label_line(row['name'])
    summary, more, example = _split_effect_text(effect)
    more_text = _effect_more_text(effect)
    sentence_count = _count_sentences(effect)

    if sentence_count >= 3 and (more_text or example):
        type_name = (row['type'] or 'unknown').replace('-', ' ').title() if row['type'] else 'Unknown'
        category_name = (row['category'] or 'unknown').replace('-', ' ').title() if row['category'] else 'Unknown'
        prompt_lines = [
            f"{name} ({type_name} {category_name})",
        ]
        if move_label:
            prompt_lines.append(move_label)
        prompt_lines.extend([
            f"Power: {row['power'] if row['power'] is not None else '—'} | Accuracy: {row['accuracy'] if row['accuracy'] is not None else '—'} | PP: {row['pp'] if row['pp'] is not None else '—'}",
            f"Effect: {summary or _effect_summary(effect)}",
        ])
        question = _make_followup_prompt(name, 'move', summary or _effect_summary(effect), more_text, example)
        if question:
            prompt_lines.append(question.split("\n", 1)[1])
            return "\n".join(prompt_lines), {
                'type': 'followup',
                'category': 'move',
                'name': name,
                'more': more_text,
                'example': example,
            }

    return format_response("move", row), None


def handle_item_context(entity):
    row = _find_by_name("items", entity)
    if not row:
        return None, None

    effect = row['effect'] if row['effect'] is not None else row['short_effect'] if row['short_effect'] is not None else ''
    name = row['name'].title() if row['name'] else 'Item'
    summary, more, example = _split_effect_text(effect)
    more_text = _effect_more_text(effect)
    sentence_count = _count_sentences(effect)

    if sentence_count >= 3 and (more_text or example):
        prompt = _make_followup_prompt(name, 'item', summary or _effect_summary(effect), more_text, example)
        if prompt:
            return prompt, {
                'type': 'followup',
                'category': 'item',
                'name': name,
                'more': more_text,
                'example': example,
            }

    return f"{name}: {_effect_summary(effect)}", None


def _select_latest_game_for_pokemon(pokemon_name):
    rows = fetch_all(
        "SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE lower(pokemon)=? GROUP BY game",
        (pokemon_name.lower(),),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def _select_latest_game_for_move(move_name):
    rows = fetch_all(
        "SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE lower(move)=? GROUP BY game",
        (move_name.lower(),),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def _select_latest_game_for_pokemon_in_generation(pokemon_name, generation):
    gen_games = GENERATION_GAMES.get((generation or "").lower(), [])
    if not gen_games:
        return None
    placeholders = ",".join(["?"] * len(gen_games))
    rows = fetch_all(
        f"SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE lower(pokemon)=? AND lower(game) IN ({placeholders}) GROUP BY game",
        tuple([pokemon_name.lower(), *[g.lower() for g in gen_games]]),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def _select_latest_game_for_move_in_generation(move_name, generation):
    gen_games = GENERATION_GAMES.get((generation or "").lower(), [])
    if not gen_games:
        return None
    placeholders = ",".join(["?"] * len(gen_games))
    rows = fetch_all(
        f"SELECT game, COUNT(*) AS cnt FROM pokemon_moves WHERE lower(move)=? AND lower(game) IN ({placeholders}) GROUP BY game",
        tuple([move_name.lower(), *[g.lower() for g in gen_games]]),
    )
    if not rows:
        return None
    best = max(rows, key=lambda r: (_game_rank(r['game']), int(r['cnt'] or 0), _normalize_game_key(r['game'])))
    return best['game']


def handle_pokemon_moves(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a pokemon name, for example: what moves can mudkip learn?", None

    pokemon_query = (entity.get('pokemon') or '').strip()
    game = (entity.get('game') or '').strip() or None
    generation = (entity.get('generation') or '').strip() or None
    if not pokemon_query:
        return "Please include a pokemon name, for example: what moves can mudkip learn?", None

    pokemon_row = _find_by_name("pokemon", pokemon_query)
    if not pokemon_row:
        return "Pokémon not found.", None
    pokemon_name = pokemon_row['name']

    try:
        selected_game = game or _select_latest_game_for_pokemon_in_generation(pokemon_name, generation) or _select_latest_game_for_pokemon(pokemon_name)
        if not selected_game:
            return f"No move learnset data found for {pokemon_name.title()}.", None

        rows = fetch_all(
            """
            SELECT pm.move, pm.method, pm.level, m.type
            FROM pokemon_moves pm
            LEFT JOIN moves m ON lower(m.name)=lower(pm.move)
            WHERE lower(pm.pokemon)=?
              AND (lower(pm.game)=? OR lower(pm.game)=? OR lower(pm.game)=?)
            ORDER BY pm.method, pm.level IS NULL, pm.level, pm.move
            """,
            (
                pokemon_name.lower(),
                selected_game.lower(),
                selected_game.lower().replace(' ', ''),
                selected_game.lower().replace(' ', '-'),
            ),
        )

        if not rows and game:
            rows = fetch_all(
                """
                SELECT pm.move, pm.method, pm.level, m.type
                FROM pokemon_moves pm
                LEFT JOIN moves m ON lower(m.name)=lower(pm.move)
                WHERE lower(pm.pokemon)=?
                  AND (lower(pm.game) LIKE ? OR lower(pm.game) LIKE ?)
                ORDER BY pm.method, pm.level IS NULL, pm.level, pm.move
                """,
                (
                    pokemon_name.lower(),
                    f"%{selected_game.lower().replace(' ', '')}%",
                    f"%{selected_game.lower().replace(' ', '-')}%",
                ),
            )

        if not rows:
            return f"No move learnset data found for {pokemon_name.title()} in {_display_game_name(selected_game)}.", None

        grouped = {"level-up": [], "machine": [], "tutor": []}
        seen = set()
        for row in rows:
            method = (row['method'] or '').lower()
            if method not in grouped:
                continue
            key = (method, row['move'], row['level'])
            if key in seen:
                continue
            seen.add(key)
            grouped[method].append(row)

        lines = [f"{pokemon_name.title()} moves in {_display_game_name(selected_game)}:"]

        sections = [
            ("Level-Up Moves", "level-up"),
            ("TM/HM Moves", "machine"),
            ("Move Tutor Moves", "tutor"),
        ]
        for heading, key in sections:
            lines.append("")
            lines.append(f"{heading}:")
            section_rows = grouped.get(key) or []
            if not section_rows:
                lines.append("- None")
                continue
            for row in section_rows:
                move_name = (row['move'] or 'Unknown Move').replace('-', ' ').title()
                type_name = (row['type'] or 'Unknown').replace('-', ' ').title()
                lines.append(f"- Lv {_format_learn_level(row['level'], row['method'])} | {move_name} | {type_name}")

        return "\n".join(lines), None
    except sqlite3.OperationalError:
        return "Move learnset data is not available yet. Run tools/build_database.py to load pokemon move learnsets.", None


def handle_move_learners(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a move name, for example: what pokemon can learn the move earthquake?", None

    move_query = (entity.get('move') or '').strip()
    game = (entity.get('game') or '').strip() or None
    generation = (entity.get('generation') or '').strip() or None
    if not move_query:
        return "Please include a move name, for example: what pokemon can learn the move earthquake?", None

    move_row = _find_by_name("moves", move_query)
    if not move_row:
        return "Move not found.", None
    move_name = move_row['name']

    try:
        selected_game = game or _select_latest_game_for_move_in_generation(move_name, generation) or _select_latest_game_for_move(move_name)
        if not selected_game:
            return f"No learner data found for {move_name.title()}.", None

        rows = fetch_all(
            """
            SELECT pm.pokemon, pm.method, pm.level
            FROM pokemon_moves pm
            WHERE lower(pm.move)=?
              AND (lower(pm.game)=? OR lower(pm.game)=? OR lower(pm.game)=?)
            ORDER BY pm.method, pm.level IS NULL, pm.level, pm.pokemon
            """,
            (
                move_name.lower(),
                selected_game.lower(),
                selected_game.lower().replace(' ', ''),
                selected_game.lower().replace(' ', '-'),
            ),
        )

        if not rows and game:
            rows = fetch_all(
                """
                SELECT pm.pokemon, pm.method, pm.level
                FROM pokemon_moves pm
                WHERE lower(pm.move)=?
                  AND (lower(pm.game) LIKE ? OR lower(pm.game) LIKE ?)
                ORDER BY pm.method, pm.level IS NULL, pm.level, pm.pokemon
                """,
                (
                    move_name.lower(),
                    f"%{selected_game.lower().replace(' ', '')}%",
                    f"%{selected_game.lower().replace(' ', '-')}%",
                ),
            )

        if not rows:
            return f"No learner data found for {move_name.title()} in {_display_game_name(selected_game)}.", None

        grouped = {"level-up": [], "machine": [], "tutor": []}
        seen = set()
        for row in rows:
            method = (row['method'] or '').lower()
            if method not in grouped:
                continue
            key = (method, row['pokemon'], row['level'])
            if key in seen:
                continue
            seen.add(key)
            grouped[method].append(row)

        lines = [f"Pokemon that can learn {move_name.replace('-', ' ').title()} in {_display_game_name(selected_game)}:"]
        sections = [
            ("Level-Up", "level-up"),
            ("TM/HM", "machine"),
            ("Move Tutor", "tutor"),
        ]
        for heading, key in sections:
            lines.append("")
            lines.append(f"{heading}:")
            section_rows = grouped.get(key) or []
            if not section_rows:
                lines.append("- None")
                continue
            for row in section_rows:
                pokemon_name = (row['pokemon'] or 'Unknown Pokemon').replace('-', ' ').title()
                lines.append(f"- {pokemon_name} | Lv {_format_learn_level(row['level'], row['method'])}")

        return "\n".join(lines), None
    except sqlite3.OperationalError:
        return "Move learnset data is not available yet. Run tools/build_database.py to load pokemon move learnsets.", None


def handle_ability_learners(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with an ability name, for example: what pokemon can have flame body?", None

    ability_query = (entity.get('ability') or '').strip()
    game = (entity.get('game') or '').strip() or None
    generation = (entity.get('generation') or '').strip() or None
    if not ability_query:
        return "Please include an ability name, for example: what pokemon can have no guard?", None

    ability_row = _find_by_name("abilities", ability_query)
    if not ability_row:
        return "Ability not found.", None
    ability_name = (ability_row['name'] or ability_query).lower()

    try:
        query = """
            SELECT
                p.name,
                CASE
                    WHEN lower(p.hidden_ability)=? THEN 'Hidden Ability'
                    WHEN lower(p.ability_1)=? THEN 'Ability 1'
                    WHEN lower(p.ability_2)=? THEN 'Ability 2'
                    ELSE 'Ability'
                END AS slot
            FROM pokemon p
            WHERE (
                lower(p.ability_1)=?
                OR lower(p.ability_2)=?
                OR lower(p.hidden_ability)=?
            )
        """
        params = [ability_name, ability_name, ability_name, ability_name, ability_name, ability_name]

        if generation:
            gen_games = GENERATION_GAMES.get(generation.lower(), [])
            if gen_games:
                placeholders = ",".join(["?"] * len(gen_games))
                query += f"""
                    AND EXISTS (
                        SELECT 1
                        FROM pokemon_moves pmg
                        WHERE lower(pmg.pokemon)=lower(p.name)
                          AND lower(pmg.game) IN ({placeholders})
                    )
                """
                params.extend([g.lower() for g in gen_games])
            else:
                query += " AND lower(p.generation)=?"
                params.append(generation.lower())

        if game:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM pokemon_moves pm
                    WHERE lower(pm.pokemon)=lower(p.name)
                      AND (
                          lower(pm.game)=?
                          OR lower(pm.game)=?
                          OR lower(pm.game)=?
                          OR lower(pm.game) LIKE ?
                          OR lower(pm.game) LIKE ?
                      )
                )
            """
            params.extend([
                game.lower(),
                game.lower().replace(' ', ''),
                game.lower().replace(' ', '-'),
                f"%{game.lower().replace(' ', '')}%",
                f"%{game.lower().replace(' ', '-')}%",
            ])

        query += " ORDER BY p.name"
        rows = fetch_all(query, tuple(params))
        if not rows:
            parts = []
            if generation:
                parts.append(generation.title())
            if game:
                parts.append(_display_game_name(game))
            scope = f" in {' and '.join(parts)}" if parts else ""
            return f"No pokemon found with {ability_row['name'].title()}{scope}.", None

        heading = f"Pokemon that can have {ability_row['name'].title()}"
        details = []
        if generation:
            details.append(generation.title())
        if game:
            details.append(_display_game_name(game))
        if details:
            heading += f" in {' and '.join(details)}"
        heading += ":"

        lines = [heading]
        for row in rows:
            pokemon_name = (row['name'] or 'Unknown Pokemon').replace('-', ' ').title()
            slot = row['slot'] or 'Ability'
            lines.append(f"- {pokemon_name} | {slot}")
        return "\n".join(lines), None
    except sqlite3.OperationalError:
        return "Ability filter by game is not available yet. Run tools/build_database.py to load pokemon move learnsets.", None


def handle_apricorn_recipe(item_name, game=None):
    if not item_name:
        return "Please specify an item to craft, for example: how do I make an ultra ball?", None

    normalized_game = game.lower().replace(' ', '') if game else None

    if game:
        rows = fetch_all(
            "SELECT game, item, ingredient, quantity, notes FROM apricorn_recipes WHERE lower(item)=? AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY ingredient",
            (item_name.lower(), game.lower(), normalized_game, game.lower().replace(' ', '-')),
        )
    else:
        rows = fetch_all(
            "SELECT game, item, ingredient, quantity, notes FROM apricorn_recipes WHERE lower(item)=? ORDER BY game, ingredient",
            (item_name.lower(),),
        )

    if not rows:
        # fallback fuzzy name lookup
        if game:
            rows = fetch_all(
                "SELECT game, item, ingredient, quantity, notes FROM apricorn_recipes WHERE lower(item) LIKE ? AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY game, ingredient",
                (f"%{item_name.lower()}%", game.lower(), normalized_game, game.lower().replace(' ', '-')),
            )
        else:
            rows = fetch_all(
                "SELECT game, item, ingredient, quantity, notes FROM apricorn_recipes WHERE lower(item) LIKE ? ORDER BY game, ingredient",
                (f"%{item_name.lower()}%",),
            )

    if not rows:
        supported_balls = [
            "Fast Ball",
            "Lure Ball",
            "Moon Ball",
            "Friend Ball",
            "Love Ball",
            "Heavy Ball",
            "Level Ball",
        ]
        return (
            f"I don't have a Gen 2-4 apricorn recipe for {item_name.title()}. "
            f"Supported apricorn balls are: {', '.join(supported_balls)}.",
            None,
        )

    recipe_item = rows[0]['item'].title() if rows[0]['item'] else item_name.title()
    if game:
        recipe_label = game.title()
    else:
        recipe_games = sorted({(row['game'] or '').replace('-', ' ').title() for row in rows if row['game']})
        if recipe_games:
            recipe_label = "Gen 2-4"
        else:
            recipe_label = 'Unknown Game'

    ingredients_map = {}
    notes = None
    for row in rows:
        ingredient = row['ingredient'].replace('-', ' ').title() if row['ingredient'] else 'Unknown Ingredient'
        qty = row['quantity'] if row['quantity'] is not None else 0
        if ingredient not in ingredients_map or qty > ingredients_map[ingredient]:
            ingredients_map[ingredient] = qty
        if notes is None and row['notes']:
            notes = row['notes']

    apricorn_total = sum(qty for ingredient, qty in ingredients_map.items() if 'Apricorn' in ingredient)
    ingredients = [f"- {ingredient}: {qty}" for ingredient, qty in sorted(ingredients_map.items())]

    response = [f"How to craft {recipe_item} ({recipe_label}):", *ingredients, f"Apricorns needed: {apricorn_total}"]
    if notes:
        response.append(f"Notes: {notes}")
    return "\n".join(response), None


def handle_item(entity):
    if not entity:
        return "Please ask about an item, for example: what does max potion do?", None

    if isinstance(entity, dict):
        item_name = (entity.get('name') or '').strip()
        action = entity.get('action')
        game = entity.get('game')
        if not item_name:
            return "Please include the item name in your question.", None
        if action == 'craft':
            return handle_apricorn_recipe(item_name, game)
        response, followup = handle_item_context(item_name)
        if response is not None:
            return response, followup
        # if user asked item lookup but we only have crafting recipe, still answer.
        recipe_response, recipe_followup = handle_apricorn_recipe(item_name, game)
        if not recipe_response.startswith("I don't have apricorn crafting data"):
            return recipe_response, recipe_followup
        return "Item not found.", None

    response, followup = handle_item_context(entity)
    if response is not None:
        return response, followup
    return handle_apricorn_recipe(entity)


def _split_multi_terms(value):
    text = re.sub(r"\s+", " ", (value or "").strip())
    if not text:
        return []
    text = text.replace(",", " and ")
    parts = [p.strip() for p in re.split(r"\band\b", text) if p.strip()]
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]


def _is_known_egg_group(value):
    if not value:
        return False
    row = fetch_one("SELECT 1 FROM pokemon_egg_groups WHERE lower(egg_group)=? LIMIT 1", (value.lower(),))
    return bool(row)


def _extract_multi_filters(query_text):
    q = re.sub(r"\s+", " ", (query_text or "").strip().lower())

    type_filters = [m.group(1).strip() for m in re.finditer(r"\b(normal|fire|water|electric|grass|ice|fighting|poison|ground|flying|psychic|bug|rock|ghost|dragon|dark|steel|fairy)\s+type\b", q)]
    type_filters = [t for t in type_filters if t in POKEMON_TYPES]

    egg_group_filters = []
    if "egg group" in q or "egg groups" in q:
        share_match = re.search(r"\bshare\s+(.+?)\s+egg groups?\b", q)
        in_match = re.search(r"\bin\s+(?:the\s+)?(.+?)\s+egg groups?\b", q)
        leading_match = re.search(r"\b([a-z0-9\- ]+?)\s+egg groups?\b", q)
        egg_phrase = None
        if share_match:
            egg_phrase = share_match.group(1)
        elif in_match:
            egg_phrase = in_match.group(1)
        elif leading_match:
            egg_phrase = leading_match.group(1)
        if egg_phrase:
            egg_phrase = re.sub(r"\b(what|which|pokemon|are|is|the|in|with|of|that|can|learn|share)\b", "", egg_phrase)
            egg_phrase = re.sub(r"\s+", " ", egg_phrase).strip()
            egg_group_filters = [_normalize_egg_group_name(p) for p in _split_multi_terms(egg_phrase)]

    if not egg_group_filters:
        shorthand_match = re.search(r"^(.+?)\s+pokemon\b", q)
        if shorthand_match:
            candidate = shorthand_match.group(1).strip()
            if candidate and "type" not in candidate and "learn" not in candidate:
                maybe_groups = [_normalize_egg_group_name(p) for p in _split_multi_terms(candidate)]
                maybe_groups = [g for g in maybe_groups if _is_known_egg_group(g)]
                if maybe_groups:
                    egg_group_filters = maybe_groups

    move_filters = []
    learn_match = re.search(r"\b(?:can\s+learn|learn)\s+(.+)$", q)
    if learn_match:
        learn_part = learn_match.group(1)
        learn_part = re.split(r"\b(?:with|that|who|which)\b", learn_part, maxsplit=1)[0].strip()
        learn_part = re.split(r"\band\s+(?:have|has|with)\b", learn_part, maxsplit=1)[0].strip()
        learn_part = re.split(r"\band\s+in\s+(?:the\s+)?[a-z0-9\- ]+\s+egg\s+groups?\b", learn_part, maxsplit=1)[0].strip()
        move_filters = _split_multi_terms(learn_part)

    ability_filter = None
    with_match = re.search(r"\bwith\s+(.+?)(?=\s+(?:can\s+learn|learn|in\s+the\s+|in\s+|that\s+|who\s+|which\s+)|$)", q)
    if with_match:
        candidate = with_match.group(1).strip()
        if "egg group" not in candidate and not re.search(r"\btype\b", candidate):
            ability_filter = candidate

    can_have_match = re.search(r"\bcan\s+have\s+(.+?)(?=\s+(?:can\s+learn|learn|in\b|and\b)|$)", q)
    if can_have_match and not ability_filter:
        candidate = can_have_match.group(1).strip()
        if "egg group" not in candidate and not re.search(r"\btype\b", candidate):
            ability_filter = candidate

    and_have_match = re.search(r"\band\s+have\s+(.+?)(?=\s+(?:can\s+learn|learn|in\b)|$)", q)
    if and_have_match and not ability_filter:
        candidate = and_have_match.group(1).strip()
        if "egg group" not in candidate and not re.search(r"\btype\b", candidate):
            ability_filter = candidate

    return {
        "types": [t for t in type_filters if t],
        "egg_groups": [g for g in egg_group_filters if g],
        "moves": [m for m in move_filters if m],
        "ability": ability_filter,
    }


def handle_multi_filter(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with pokemon qualifiers like moves, egg groups, types, or abilities.", None

    query_text = (entity.get('query') or '').strip()
    game = (entity.get('game') or '').strip() or None
    if not query_text:
        return "Please include filter details in your query.", None

    filters = _extract_multi_filters(query_text)
    type_filters = filters['types']
    egg_group_filters = filters['egg_groups']
    move_queries = filters['moves']
    ability_query = (filters['ability'] or '').strip()

    if len(type_filters) + len(egg_group_filters) + len(move_queries) + (1 if ability_query else 0) < 2:
        return "Please include at least two qualifiers (move, type, egg group, or ability).", None

    resolved_moves = []
    for move_query in move_queries:
        move_row = _find_by_name("moves", move_query)
        if not move_row:
            return f"Move not found: {move_query}", None
        resolved_moves.append(move_row['name'].lower())

    resolved_ability = None
    if ability_query:
        ability_row = _find_by_name("abilities", ability_query)
        if not ability_row:
            return f"Ability not found: {ability_query}", None
        resolved_ability = ability_row['name'].lower()

    base_rows = fetch_all("SELECT lower(name) AS n FROM pokemon")
    candidates = {r['n'] for r in base_rows if r and r['n']}

    for t in type_filters:
        rows = fetch_all("SELECT lower(name) AS n FROM pokemon WHERE lower(type1)=? OR lower(type2)=?", (t, t))
        type_set = {r['n'] for r in rows if r and r['n']}
        candidates &= type_set

    for g in egg_group_filters:
        rows = fetch_all("SELECT lower(pokemon) AS n FROM pokemon_egg_groups WHERE lower(egg_group)=?", (g.lower(),))
        group_set = {r['n'] for r in rows if r and r['n']}
        candidates &= group_set

    if resolved_ability:
        rows = fetch_all(
            "SELECT lower(name) AS n FROM pokemon WHERE lower(ability_1)=? OR lower(ability_2)=? OR lower(hidden_ability)=?",
            (resolved_ability, resolved_ability, resolved_ability),
        )
        ability_set = {r['n'] for r in rows if r and r['n']}
        candidates &= ability_set

    for mv in resolved_moves:
        query = [
            "SELECT DISTINCT lower(p.name) AS n",
            "FROM pokemon p",
            "JOIN pokemon_moves pm ON (lower(pm.pokemon)=lower(p.name) OR lower(pm.pokemon) LIKE lower(p.name) || ' %')",
            "WHERE lower(pm.move)=?",
        ]
        params = [mv]
        if game:
            g = game.lower()
            gp = g.replace(' ', '')
            gh = g.replace(' ', '-')
            query.append("AND (lower(pm.game)=? OR lower(pm.game)=? OR lower(pm.game)=? OR lower(pm.game) LIKE ? OR lower(pm.game) LIKE ?)")
            params.extend([g, gp, gh, f"%{gp}%", f"%{gh}%"])
        rows = fetch_all("\n".join(query), tuple(params))
        move_set = {r['n'] for r in rows if r and r['n']}
        candidates &= move_set

    if not candidates:
        return "There aren't any pokemon.", None

    placeholders = ",".join(["?"] * len(candidates))
    rows = fetch_all(
        f"SELECT name, COALESCE(pokedex_number, id, 99999) AS order_key FROM pokemon WHERE lower(name) IN ({placeholders}) ORDER BY order_key, name",
        tuple(sorted(candidates)),
    )
    if not rows:
        return "There aren't any pokemon.", None

    grouped_rows = [{"pokemon": r['name'], "order_key": r['order_key']} for r in rows if r and r['name']]
    body_lines = _format_egg_group_member_lines(grouped_rows)
    header = "Pokemon matching qualifiers"
    if game:
        header += f" in {_display_game_name(game)}"
    lines = [header + ":"]
    lines.extend(body_lines)
    return "\n".join(lines), None


def _mainline_games_from_rows(rows):
    games = set()
    for r in rows:
        game_name = r['game'] if isinstance(r, sqlite3.Row) else (r[0] if r else None)
        if not game_name:
            continue
        if _game_rank(game_name) < 0:
            continue
        games.add(_normalize_game_key(game_name))
    return sorted(games, key=lambda g: (_game_rank(g), g))


def handle_pokemon_games(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a pokemon name, for example: what games is beldum in?", None

    pokemon_query = (entity.get('pokemon') or '').strip()
    if not pokemon_query:
        return "Please include a pokemon name, for example: beldum games?", None

    pokemon_row = _find_by_name("pokemon", pokemon_query)
    if not pokemon_row:
        return "Pokémon not found.", None

    name = pokemon_row['name']
    rows = fetch_all(
        "SELECT DISTINCT game FROM pokemon_moves WHERE lower(pokemon)=? OR lower(pokemon) LIKE ?",
        (name.lower(), f"{name.lower()} %"),
    )
    games = _mainline_games_from_rows(rows)
    if not games:
        return f"No mainline game support data found for {name.title()}.", None

    display_games = [_display_game_name(g) for g in games]
    lines = [f"Mainline games with {name.title()} support:"]
    lines.extend([f"- {g}" for g in display_games])
    return "\n".join(lines), None


def handle_pokemon_catch_games(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a pokemon name, for example: what games can you catch beldum in?", None

    pokemon_query = (entity.get('pokemon') or '').strip()
    if not pokemon_query:
        return "Please include a pokemon name, for example: what games can you catch beldum in?", None

    pokemon_row = _find_by_name("pokemon", pokemon_query)
    if not pokemon_row:
        return "Pokémon not found.", None

    name = pokemon_row['name']
    rows = fetch_all(
        "SELECT DISTINCT game FROM encounters WHERE lower(pokemon)=?",
        (name.lower(),),
    )
    games = _mainline_games_from_rows(rows)
    if not games:
        return f"No mainline wild encounter data found for {name.title()}.", None

    display_games = [_display_game_name(g) for g in games]
    lines = [f"Mainline games where {name.title()} can be caught in the wild:"]
    lines.extend([f"- {g}" for g in display_games])
    return "\n".join(lines), None


def handle_pokemon_presence(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask with a pokemon and game, for example: is beldum in silver?", None

    pokemon_query = (entity.get('pokemon') or '').strip()
    game = (entity.get('game') or '').strip() or None
    if not pokemon_query:
        return "Please include a pokemon name.", None
    if not game:
        return "Please include a mainline game, for example: is beldum in omega ruby?", None

    pokemon_row = _find_by_name("pokemon", pokemon_query)
    if not pokemon_row:
        return "Pokémon not found.", None

    name = pokemon_row['name']
    game_key = _normalize_game_key(game)
    game_display = _display_game_name(game_key)
    if _game_rank(game_key) < 0:
        return "I only support mainline games for that query.", None

    support_rows = fetch_all(
        "SELECT DISTINCT game FROM pokemon_moves WHERE lower(pokemon)=? OR lower(pokemon) LIKE ?",
        (name.lower(), f"{name.lower()} %"),
    )
    support_games = set(_mainline_games_from_rows(support_rows))
    if game_key not in support_games:
        return f"No, {name.title()} is not in {game_display}.", None

    encounter_rows = fetch_all(
        """
        SELECT * FROM encounters
        WHERE lower(pokemon)=?
          AND (lower(game)=? OR lower(game)=? OR lower(game)=? OR lower(game) LIKE ? OR lower(game) LIKE ?)
        ORDER BY game, location_name, route, pokemon
        """,
        (name.lower(), game_key, game_key.replace(' ', ''), game_key.replace(' ', '-'), f"%{game_key.replace(' ', '')}%", f"%{game_key.replace(' ', '-')}%"),
    )

    if not encounter_rows:
        return f"Yes, but only if you trade/migrate from another game. {name.title()} has no wild encounter data in {game_display}.", None

    methods = sorted({(_safe_row_value(r, 'method') or 'unknown').replace('-', ' ').title() for r in encounter_rows})
    lines = [
        f"Yes, {name.title()} is in {game_display}.",
        f"Available by: {', '.join(methods)}",
        f"Encounters in {game_display}:",
        format_response("location", encounter_rows),
    ]
    return "\n".join(lines), None


def handle_followup(context, user_input):
    if not context or context.get('type') != 'followup':
        return "I don't have a follow-up question pending.", None

    answer = user_input.lower().strip()
    wants_example = bool(re.search(r"\b(example|examples)\b", answer))
    wants_more = bool(re.search(r"\b(know more|more|details|detail)\b", answer))
    wants_both = bool(re.search(r"\b(both)\b", answer))
    wants_affirmative = bool(re.search(r"\b(yes|sure|yeah|yep|y)\b", answer))
    negative = bool(re.search(r"\b(no|not now|nah)\b", answer))

    if wants_both or wants_affirmative:
        if context.get('example') and context.get('more'):
            parts = []
            if context['example']:
                parts.append(f"Example: {context['example']}")
            if context['more']:
                parts.append(f"More:\n{context['more']}")
            return "\n".join(parts), None
        if context.get('example'):
            return f"Example: {context['example']}", None
        if context.get('more'):
            return f"More:\n{context['more']}", None
        return "Okay.", None

    if wants_example:
        if context.get('example'):
            return f"Example: {context['example']}", None
        if context.get('more'):
            return "No example is available; reply 'know more' to see more detail, or 'no' to cancel.", context
        return "No example is available.", None

    if wants_more:
        if context.get('more'):
            return f"More:\n{context['more']}", None
        if context.get('example'):
            return "No more details are available; reply 'example' to see an example, or 'no' to cancel.", context
        return "No additional details are available.", None

    if negative:
        return "Okay.", None

    return "Please reply with 'example', 'know more', 'both', or 'no'.", context


def handle_query_with_context(text):
    # quick evolution-level question handling: "what level does mudkip evolve"
    evo_match = re.match(r"^\s*(?:what level does|when does|what level will|at what level does)\s+(.+?)\s+evolv", text.strip(), re.IGNORECASE)
    if evo_match:
        name = evo_match.group(1).strip()
        rows = fetch_all(
            "SELECT evolves_to, method, min_level FROM evolutions WHERE lower(pokemon)=? ORDER BY min_level IS NOT NULL, min_level",
            (name.lower(),)
        )
        if rows:
            parts = []
            for r in rows:
                to = r[0].title() if r[0] else 'Unknown'
                method = r[1] or 'level-up'
                lvl = r[2]
                if lvl:
                    parts.append(f"{name.title()} evolves into {to} at level {lvl} (method: {method}).")
                else:
                    parts.append(f"{name.title()} evolves into {to} via {method}.")
            return " ".join(parts), None

    parsed = parse(text)
    intent = parsed["intent"]
    entity = parsed.get("entity")

    if intent == "ability":
        response, followup = handle_ability_context(entity)
        if response is not None:
            return response, followup
        response, followup = handle_item_context(entity)
        if response is not None:
            return response, followup
        response, followup = handle_move_context(entity)
        if response is not None:
            return response, followup
        return "Ability not found.", None

    if intent == "move":
        response, followup = handle_move_context(entity)
        if response is not None:
            return response, followup
        response, followup = handle_ability_context(entity)
        if response is not None:
            return response, followup
        response, followup = handle_item_context(entity)
        if response is not None:
            return response, followup
        return "Move not found.", None

    if intent == "item":
        return handle_item(entity)

    if intent == "route":
        response, followup = handle_route(entity)
        return response, followup

    handler = HANDLERS.get(intent, handle_unknown)
    result = handler(entity)
    if isinstance(result, tuple) and len(result) == 2:
        response, followup = result
    else:
        response, followup = result, None

    # For unknown intent, only try location fallback after direct entity lookup
    # has failed. This avoids pokemon names like "diglett" being hijacked by
    # location names like "digletts cave".
    if handler == handle_unknown and entity and isinstance(entity, str):
        unknown_msg = "I don't understand that yet. Try asking about a Pokémon, ability, move, location, or gym."
        if response == unknown_msg:
            # Single-term lookups like "intimidate" or "flamethrower" should still resolve.
            for resolver in (handle_ability_context, handle_move_context, handle_item_context):
                candidate_response, candidate_followup = resolver(entity)
                if candidate_response is not None:
                    return candidate_response, candidate_followup

            if re.match(r"^(?:g\s*max|gmax|max|g)\s+[a-z0-9][a-z0-9\s-]*$", entity.strip().lower()):
                return "Move not found.", None

            e = entity.lower()
            rows = fetch_all(
                "SELECT * FROM encounters WHERE lower(location_name) LIKE ? OR lower(location_area) LIKE ? OR lower(route) LIKE ? ORDER BY game, location_name, route, pokemon",
                (f"%{e}%", f"%{e}%", f"%{e}%"),
            )
            if rows:
                return format_response("location", rows), None

            # if the user provided a location plus a game (e.g. 'bell tower crystal'),
            # try splitting into location + game and search accordingly
            parts = e.split()
            if len(parts) >= 2:
                candidate_game = parts[-1]
                candidate_loc = ' '.join(parts[:-1])
                normalized_game = candidate_game.replace(' ', '')
                rows = fetch_all(
                    "SELECT * FROM encounters WHERE (lower(location_name) LIKE ? OR lower(location_area) LIKE ?) AND (lower(game) LIKE ? OR lower(game) LIKE ?) ORDER BY game, location_name, pokemon",
                    (f"%{candidate_loc}%", f"%{candidate_loc}%", f"%{normalized_game}%", f"%{candidate_game.replace(' ', '-') }%"),
                )
                if rows:
                    return format_response("location", rows), None

    return response, followup


def handle_route_followup(context, user_input):
    if not context or context.get('type') != 'route_followup':
        return "I don't have a route question pending.", None
    
    route = context.get('route')
    game = user_input.strip()
    
    if not game:
        return "Please specify a game.", context
    
    normalized_game = game.lower().replace(" ", "")
    exact_game = game.lower().replace(" ", "")
    hyphen_game = game.lower().replace(' ', '-')
    exact_rows = fetch_all(
        "SELECT * FROM encounters WHERE (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY game, route, pokemon",
        (exact_game, hyphen_game, game.lower())
    )
    exact_rows = [r for r in exact_rows if _route_matches(r['route'], route)]
    if exact_rows:
        return format_response("route", exact_rows), None
    query = "SELECT * FROM encounters WHERE (lower(game) LIKE ? OR lower(game) LIKE ?) ORDER BY game, route, pokemon"
    rows = fetch_all(query, (f"%{normalized_game}%", f"%{hyphen_game}%"))
    rows = [r for r in rows if _route_matches(r['route'], route)]
    
    if rows:
        return format_response("route", rows), None
    
    return f"No encounters found for Route {route} in {game.title()}. Would you like to try a different game?", context


def handle_gym_followup(context, user_input):
    if not context or context.get('type') != 'gym_followup':
        return "I don't have a gym question pending.", None
    number = context.get('number')
    game = user_input.strip()
    if not game:
        return "Please specify a game.", context
    normalized_game = game.lower().replace(' ', '')
    hyphen_game = game.lower().replace(' ', '-')
    row = fetch_one(
        "SELECT * FROM gyms WHERE gym_number=? AND (lower(game)=? OR lower(game)=? OR lower(game)=?)",
        (number, normalized_game, hyphen_game, game.lower())
    )
    if not row:
        row = fetch_one("SELECT * FROM gyms WHERE gym_number=? AND lower(game) LIKE ?", (number, f"%{normalized_game}%"))
    if not row:
        return f"No gym {number} found for {game.title()}.", context
    teams = fetch_all(
        "SELECT pokemon, position FROM gym_teams WHERE gym_number=? AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY position",
        (number, normalized_game, hyphen_game, game.lower())
    )
    team_list = [t['pokemon'].title() for t in teams] if teams else []
    leader = row['leader'].title() if row['leader'] else 'Leader'
    city = row['city'].title() if row['city'] else ''
    gym_type = row['type'].title() if row['type'] else 'Unknown'
    badge = row['badge'] if row['badge'] else ''
    resp = f"Gym {number} — {city}\nLeader: {leader}"
    resp += f"\nSpecialty Type: {gym_type}"
    if team_list:
        resp += f"\nTeam: {', '.join(team_list)}"
    if badge:
        resp += f"\nBadge: {badge}"
    return resp, None


def handle_location_followup(context, user_input):
    if not context or context.get('type') != 'location_followup':
        return "I don't have a location question pending.", None
    location = context.get('location')
    game = user_input.strip()
    if not game:
        return "Please specify a game.", context
    game_key = _normalize_game_key(game)
    normalized_game = game_key.replace(' ', '')
    exact_game = game_key
    hyphen_game = game_key.replace(' ', '-')
    exact_rows = fetch_all(
        "SELECT * FROM encounters WHERE (lower(location_name) LIKE ? OR lower(location_area) LIKE ?) AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY game, location_name, pokemon",
        (f"%{location.lower()}%", f"%{location.lower()}%", exact_game, hyphen_game, game.lower())
    )
    if exact_rows:
        return format_response("location", exact_rows), None
    return f"There are no Pokemon encounters for {location.title()} in {_display_game_name(game_key)}.", context


def interactive_handle(text, last_context=None):
    if last_context is not None:
        ttype = last_context.get('type')
        if ttype == 'gym_followup':
            return handle_gym_followup(last_context, text)
        if ttype == 'route_followup':
            return handle_route_followup(last_context, text)
        if ttype == 'location_followup':
            return handle_location_followup(last_context, text)
        if ttype == 'followup' and re.match(r"^\s*(yes|both|example|know more|more|details|detail|no|nah|sure|yeah|yep|y)\b", text.strip(), re.IGNORECASE):
            return handle_followup(last_context, text)
    return handle_query_with_context(text)


def handle(text):
    response, _ = handle_query_with_context(text)
    return response


def handle_ability(entity):
    response, _ = handle_ability_context(entity)
    return response if response is not None else "Ability not found."


def handle_pokemon(entity):
    row = _find_by_name("pokemon", entity)
    if not row:
        return "Pokémon not found."
    response = format_response("pokemon", row)
    tree = _build_evolution_tree(row["name"], entity)
    if tree:
        response += f"\n\n{tree}"
    return response


def handle_move(entity):
    row = _find_by_name("moves", entity)
    return format_response("move", row) if row else "Move not found."


def handle_location(entity):
    if not entity or not isinstance(entity, dict):
        return "I need a location and optional game to answer that.", None

    pokemon_name = entity.get("pokemon")
    location_name = entity.get("location")
    game = entity.get("game")

    if pokemon_name:
        query = "SELECT game, route, location_name, location_area, pokemon, chance, method FROM encounters WHERE lower(pokemon)=?"
        params = [pokemon_name.lower()]
        if game:
            game_key = _normalize_game_key(game)
            normalized_game = game_key.replace(' ', '')
            exact_game = game_key
            hyphen_game = game_key.replace(' ', '-')
            query += " AND (lower(game)=? OR lower(game)=? OR lower(game)=?)"
            params.extend([exact_game, hyphen_game, normalized_game])
        rows = fetch_all(query + " ORDER BY game, route, chance DESC, method", tuple(params))
        if not rows:
            if game:
                support_rows = fetch_all(
                    "SELECT DISTINCT game FROM pokemon_moves WHERE lower(pokemon)=? OR lower(pokemon) LIKE ?",
                    (pokemon_name.lower(), f"{pokemon_name.lower()} %"),
                )
                support_games = set(_mainline_games_from_rows(support_rows))
                game_key = _normalize_game_key(game)
                if game_key in support_games:
                    return f"No wild encounter routes found for {pokemon_name.title()} in {_display_game_name(game)}. It is only available via non-wild methods (e.g., trade/migrate/gift).", None
                if _game_rank(game_key) >= 0:
                    return f"No, {pokemon_name.title()} is not in {_display_game_name(game)}.", None
            return f"No encounter routes found for {pokemon_name.title()}.", None

        grouped = {}
        order = []
        for row in rows:
            route_value = row['route'] or row['location_name'] or row['location_area'] or 'Unknown location'
            route_label = route_value.replace('-', ' ').title()
            game_label = (row['game'] or '').replace('-', ' ').title()
            method_value = row['method'] or 'unknown'
            method_label = _format_encounter_method(method_value)
            key = (game_label, route_label)
            method_key = method_label
            if key not in grouped:
                grouped[key] = {
                    'game': game_label,
                    'route': route_label,
                    'methods': [],
                    'by_method': {},
                }
                order.append(key)
            if method_key not in grouped[key]['by_method']:
                grouped[key]['by_method'][method_key] = 0
                grouped[key]['methods'].append(method_key)
            grouped[key]['by_method'][method_key] += int(row['chance'] or 0)

        lines = []
        header = f"{pokemon_name.title()} encounters"
        if game:
            header += f" in {game.title()}"
        lines.append(header + ":")
        for key in order:
            entry = grouped[key]
            method_parts = [f"{method} {entry['by_method'][method]}%" for method in entry['methods']]
            methods = ", ".join(method_parts) if method_parts else "Unknown"
            lines.append(f"- {entry['route']} ({entry['game']}) - {methods}")
        return "\n".join(lines), None

    if not location_name:
        return "Please ask about a location, for example: what pokemon are in viridian forest in pokemon crystal?", None

    # Handle "where is <pokemon> in <game>" as a pokemon encounter query.
    if location_name and not pokemon_name:
        maybe_pokemon = _find_by_name("pokemon", location_name)
        if maybe_pokemon:
            return handle_location({"pokemon": maybe_pokemon['name'], "game": game})

    # if location specified but no game, ask for game to avoid returning master lists
    if location_name and not game:
        # check how many games this location appears in
        rows = fetch_all(
            "SELECT DISTINCT game FROM encounters WHERE lower(location_name) LIKE ? OR lower(location_area) LIKE ?",
            (f"%{location_name.lower()}%", f"%{location_name.lower()}%"),
        )
        games = sorted({r['game'] for r in rows}) if rows else []
        if len(games) == 0:
            return "No Pokémon found for that location.", None
        if len(games) == 1:
            # only one game — proceed
            game = games[0]
        else:
            sample = ', '.join([g.title() for g in games[:5]])
            if len(games) > 5:
                sample += ", ..."
            return f"{location_name.title()}: Which game? It appears in {sample}.", {
                'type': 'location_followup',
                'location': location_name,
            }

    query = "SELECT * FROM encounters WHERE (lower(location_name) LIKE ? OR lower(location_area) LIKE ?)"
    params = [f"%{location_name.lower()}%", f"%{location_name.lower()}%"]

    if game:
        game_key = _normalize_game_key(game)
        normalized_game = game_key.replace(' ', '')
        exact_game = game_key
        hyphen_game = game_key.replace(' ', '-')
        exact_rows = fetch_all(
            query + " AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY game, location_name, pokemon",
            (f"%{location_name.lower()}%", f"%{location_name.lower()}%", exact_game, hyphen_game, normalized_game)
        )
        if exact_rows:
            return format_response("location", exact_rows), None
        return f"There are no Pokemon encounters for {location_name.title()} in {_display_game_name(game_key)}.", None

    rows = fetch_all(query + " ORDER BY game, location_name, pokemon", tuple(params))
    if rows:
        return format_response("location", rows), None

    if game:
        return f"There are no Pokemon encounters for {location_name.title()} in {_display_game_name(game)}.", None
    return "No Pokémon found for that location.", None


def handle_tmhm(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask about TM or HM codes with a game, for example: what is TM19 in Pokémon Platinum."
    code = entity.get('code')
    game = entity.get('game')
    if not code:
        return "Please specify a TM or HM code like TM19 or HM01."
    if not game:
        return "Please include a game, for example: what is TM19 in Pokémon Platinum."
    row = fetch_one(
        "SELECT move FROM tms WHERE lower(code)=? AND lower(game)=?",
        (code.lower(), game.lower())
    )
    if row:
        return f"{code.upper()} in {game.title()} is {row['move'].replace('-', ' ').title()}."
    return f"No TM/HM mapping found for {code.upper()} in {game.title()}."


def handle_route(entity):
    if not entity or not isinstance(entity, dict):
        return "Please ask for routes by number and game, for example: route 12 ultra moon.", None

    route = entity.get("route")
    game = entity.get("game")
    
    if route and not game:
        return f"Route {route}: Which game? (e.g., Ultra Moon, Platinum, Scarlet)", {
            "type": "route_followup",
            "route": route,
        }
    
    if not route and not game:
        return "Please specify a route number, for example: route 12 in ultra moon.", None

    if not route and game:
        rows = fetch_all(
            "SELECT DISTINCT route FROM encounters WHERE (lower(game)=? OR lower(game)=? OR lower(game)=?) AND route IS NOT NULL AND trim(route) != '' ORDER BY route",
            (game.lower(), game.lower().replace(' ', ''), game.lower().replace(' ', '-')),
        )
        if rows:
            route_names = [r['route'].title() for r in rows[:30]]
            response = f"Routes in {game.title()}: " + ", ".join(route_names)
            if len(rows) > 30:
                response += f", ... ({len(rows) - 30} more)"
            return response, None
        return f"No route data found for {game.title()}.", None

    query = "SELECT * FROM encounters"
    params = []
    
    if game:
        normalized_game = game.lower().replace(" ", "")
        exact_game = game.lower().replace(" ", "")
        hyphen_game = game.lower().replace(' ', '-')
        exact_rows = fetch_all(
            query + " WHERE (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY game, route, pokemon",
            (exact_game, hyphen_game, game.lower())
        )
        exact_rows = [r for r in exact_rows if _route_matches(r['route'], route)]
        if exact_rows:
            return format_response("route", exact_rows), None
        query += " WHERE (lower(game) LIKE ? OR lower(game) LIKE ?)"
        params.append(f"%{normalized_game}%")
        params.append(f"%{hyphen_game}%")

    rows = fetch_all(query + " ORDER BY game, route, pokemon", tuple(params))
    rows = [r for r in rows if _route_matches(r['route'], route)]
    return format_response("route", rows) if rows else "No route data found.", None


def handle_egg(entity):
    if not entity:
        return "Please ask about egg groups or a Pokémon's egg groups."

    if isinstance(entity, dict):
        game = (entity.get("game") or "").strip() or None
        generation = (entity.get("generation") or "").strip() or None

        scope = None
        if game:
            scope = _display_game_name(game)
        elif generation:
            scope = generation.title()

        if entity.get("group"):
            group_name = _normalize_egg_group_name(entity["group"])
            rows = _fetch_egg_group_members(group_name, game=game, generation=generation)
            if rows:
                display_name = entity["group"].title()
                if display_name.lower() in ("normal", "human shape", "human-shaped", "humanshape", "humanlike"):
                    display_name = group_name.title()
                display_name = _format_egg_group_label(display_name)
                lines = _format_egg_group_member_lines(rows)
                body = "\n".join(lines)
                if scope:
                    return f"Pokemon in the {display_name} egg group ({scope}):\n{body}"
                return f"Pokemon in the {display_name} egg group:\n{body}"
            return "Egg group not found."

        if entity.get("pokemon"):
            pokemon_name = entity["pokemon"]
            row = _find_by_name("pokemon", pokemon_name)
            if not row:
                return "Pokémon not found."
            rows = fetch_all(
                "SELECT egg_group FROM pokemon_egg_groups WHERE lower(pokemon)=? ORDER BY egg_group",
                (row["name"].lower(),),
            )
            if not rows:
                return f"No egg group data found for {row['name'].title()}."
            groups = [_format_egg_group_label(r[0]) for r in rows]
            if scope:
                return f"Egg groups for {row['name'].title()} ({scope}): {', '.join(groups)}"
            return f"Egg groups for {row['name'].title()}: {', '.join(groups)}"

        return "I couldn't determine egg group information from that request."

    if isinstance(entity, str):
        normalized_group = _normalize_egg_group_name(entity)
        rows = _fetch_egg_group_members(normalized_group)
        if rows:
            lines = _format_egg_group_member_lines(rows)
            return f"Pokemon in the {_format_egg_group_label(entity)} egg group:\n{'\n'.join(lines)}"

        pokemon_row = _find_exact_by_name("pokemon", entity)
        if pokemon_row:
            name = pokemon_row["name"]
            rows = fetch_all(
                "SELECT egg_group FROM pokemon_egg_groups WHERE lower(pokemon)=? ORDER BY egg_group",
                (name.lower(),)
            )
            if not rows:
                return f"No egg group data found for {name.title()}."
            groups = [_format_egg_group_label(r[0]) for r in rows]
            return f"Egg groups for {name.title()}: {', '.join(groups)}"

        return "Egg group not found."


def handle_gym(entity):
    # entity may be a game string or a dict with number and game
    if not entity:
        return "Please ask about a gym by number and game, for example: gym 2 fire red.", None

    if isinstance(entity, dict):
        number = entity.get('number')
        game = entity.get('game')
        if number and not game:
            return f"Gym {number}: Which game? (e.g., Fire Red, Yellow, Ultra Moon)", {
                'type': 'gym_followup',
                'number': number,
            }
        if number and game:
            # lookup specific gym using exact game first
            normalized_game = game.lower().replace(' ', '')
            hyphen_game = game.lower().replace(' ', '-')
            row = fetch_one("SELECT * FROM gyms WHERE gym_number=? AND (lower(game)=? OR lower(game)=? OR lower(game)=?)", (number, normalized_game, hyphen_game, game.lower()))
            if not row:
                # try fuzzy game match
                row = fetch_one("SELECT * FROM gyms WHERE gym_number=? AND lower(game) LIKE ?", (number, f"%{normalized_game}%"))
            if not row:
                return f"No gym {number} found for {game.title()}.", None
            # fetch team
            teams = fetch_all("SELECT pokemon, position FROM gym_teams WHERE gym_number=? AND (lower(game)=? OR lower(game)=? OR lower(game)=?) ORDER BY position", (number, normalized_game, hyphen_game, game.lower()))
            team_list = [t['pokemon'].title() for t in teams] if teams else []
            leader = row['leader'].title() if row['leader'] else 'Leader'
            city = row['city'].title() if row['city'] else ''
            gym_type = row['type'].title() if row['type'] else 'Unknown'
            badge = row['badge'] if row['badge'] else ''
            resp = f"Gym {number} — {city}\nLeader: {leader}"
            resp += f"\nSpecialty Type: {gym_type}"
            if team_list:
                resp += f"\nTeam: {', '.join(team_list)}"
            if badge:
                resp += f"\nBadge: {badge}"
            return resp, None

    # otherwise treat entity as a game string
    if isinstance(entity, str):
        normalized = entity.lower().strip()
        exact_rows = fetch_all(
            "SELECT * FROM gyms WHERE lower(game)=? OR lower(game)=? OR lower(game)=? ORDER BY gym_number",
            (normalized, normalized.replace(' ', ''), normalized.replace(' ', '-'))
        )
        if exact_rows:
            return format_response("gyms", exact_rows), None
        rows = fetch_all(
            "SELECT * FROM gyms WHERE lower(game) LIKE ? ORDER BY gym_number",
            (f"%{normalized}%",)
        )
        return format_response("gyms", rows) if rows else "No gym data found.", None

    return "I couldn't understand that gym request.", None


def handle_unknown(entity):
    if entity:
        response, followup = handle_ability_context(entity)
        if response is not None:
            return response, followup

        row = _find_by_name("pokemon", entity)
        if row:
            response = format_response("pokemon", row)
            tree = _build_evolution_tree(row["name"])
            if tree:
                response += f"\n\n{tree}"
            return response, None

        response, followup = handle_move_context(entity)
        if response is not None:
            return response, followup

        response, followup = handle_item_context(entity)
        if response is not None:
            return response, followup

    return "I don't understand that yet. Try asking about a Pokémon, ability, move, location, or gym.", None


HANDLERS = {
    "ability": handle_ability,
    "pokemon": handle_pokemon,
    "move": handle_move,
    "multi_filter": handle_multi_filter,
    "breeding": handle_breeding,
    "pokemon_moves": handle_pokemon_moves,
    "move_learners": handle_move_learners,
    "ability_learners": handle_ability_learners,
    "pokemon_games": handle_pokemon_games,
    "pokemon_catch_games": handle_pokemon_catch_games,
    "pokemon_presence": handle_pokemon_presence,
    "item": handle_item,
    "location": handle_location,
    "route": handle_route,
    "tmhm": handle_tmhm,
    "gym": handle_gym,
    "egg": handle_egg,
    "unknown": handle_unknown,
}


def handle_ability(entity):
    response, _ = handle_ability_context(entity)
    return response if response is not None else "Ability not found."


def handle_move(entity):
    response, _ = handle_move_context(entity)
    return response if response is not None else "Move not found."


_SESSION_CONTEXT = None


def handle(text):
    """Primary entrypoint for the CLI. Persists followup context across calls so
    users can reply with just a game name (e.g. "Ultra Moon") to resolve a
    pending location/route/gym followup.
    """
    global _SESSION_CONTEXT

    # If we have a pending followup context, try to resolve it first.
    if _SESSION_CONTEXT is not None:
        ttype = _SESSION_CONTEXT.get('type')
        # If the user input looks like a real question or a longer sentence,
        # treat it as a fresh query rather than forcing it through the
        # pending followup. This prevents unrelated questions (e.g.
        # "what level does mudkip evolve") from being interpreted as a
        # game name for a pending gym/route/location followup.
        is_question = bool(re.search(r"\?", text)) or bool(re.match(r"^\s*(who|what|where|when|how|does|do|is|are|did|can|should)\b", text.strip(), re.IGNORECASE))
        word_count = len(text.strip().split()) if text.strip() else 0
        short_answer = word_count > 0 and word_count <= 4

        # followup types that expect a short game name
        if ttype in ('gym_followup', 'route_followup', 'location_followup'):
            if is_question or not short_answer:
                # treat as a new query. Only replace the pending followup if the
                # new query itself returns a followup context; otherwise keep the
                # original pending followup so the user can answer it later.
                resp, ctx = handle_query_with_context(text)
                if ctx is not None:
                    _SESSION_CONTEXT = ctx
                return resp
            # otherwise accept this short reply as the game identifier
            if ttype == 'gym_followup':
                resp, ctx = handle_gym_followup(_SESSION_CONTEXT, text)
            elif ttype == 'route_followup':
                resp, ctx = handle_route_followup(_SESSION_CONTEXT, text)
            else:
                resp, ctx = handle_location_followup(_SESSION_CONTEXT, text)
            _SESSION_CONTEXT = ctx
            return resp

        # generic followups (example/more) still respond if the user replies
        if ttype == 'followup' and re.match(r"^\s*(yes|both|example|know more|more|details|detail|no|nah|sure|yeah|yep|y)\b", text.strip(), re.IGNORECASE):
            resp, ctx = handle_followup(_SESSION_CONTEXT, text)
            _SESSION_CONTEXT = ctx
            return resp

    # No active followup context — run the regular parser/handler and capture
    # any followup context returned for the next call.
    resp, ctx = handle_query_with_context(text)
    _SESSION_CONTEXT = ctx
    return resp
