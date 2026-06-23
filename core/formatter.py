
import re


def _title(value):
    return value.title() if value else "Unknown"


Z_MOVE_BASES = {
    "acid downpour",
    "all out pummeling",
    "black hole eclipse",
    "bloom doom",
    "breakneck blitz",
    "continental crush",
    "corkscrew crash",
    "devastating drake",
    "gigavolt havoc",
    "hydro vortex",
    "inferno overdrive",
    "never ending nightmare",
    "savage spin out",
    "shattered psyche",
    "subzero slammer",
    "supersonic skystrike",
    "tectonic rage",
    "twinkle tackle",
    "catastropika",
    "10,000,000 volt thunderbolt",
    "stoked sparksurfer",
    "extreme evoboost",
    "pulverizing pancake",
    "genesis supernova",
    "sinister arrow raid",
    "malicious moonsault",
    "oceanic operetta",
    "splintered stormshards",
    "lets snuggle forever",
    "clangorous soulblaze",
    "guardian of alola",
    "soul stealing 7 star strike",
    "stokedsparksurfer",
}


def _normalize_move_name(value):
    text = (value or "").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _move_label_line(move_name):
    normalized = _normalize_move_name(move_name).lower()
    base = re.sub(r"\s+(physical|special)$", "", normalized)
    if base in Z_MOVE_BASES:
        return "(Z-Move)"
    if normalized.startswith("max ") or normalized.startswith("g max "):
        return "(G-Move)"
    return None


def _format_generation(gen_name):
    """Format generation name to display Roman numerals in uppercase."""
    if not gen_name:
        return "Unknown"
    formatted = gen_name.replace('-', ' ').title()
    # Convert Roman numerals to uppercase: replace lowercase roman numerals with uppercase
    import re
    formatted = re.sub(r'(generation\s+)([ivx]+)', lambda m: m.group(1) + m.group(2).upper(), formatted, flags=re.IGNORECASE)
    return formatted


def _row_value(row, key, default=None):
    try:
        value = row[key]
    except Exception:
        value = None
    return value if value is not None else default


TYPE_EFFECTIVENESS = {
    "normal": {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5, "ice": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "rock": 2.0, "dark": 2.0, "steel": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "ghost": 0.0, "fairy": 0.5},
    "poison": {"grass": 2.0, "fairy": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0},
    "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost": {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "fairy": 2.0, "steel": 0.5},
    "fairy": {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}


def _type_multiplier(attack_type, defense_types):
    multiplier = 1.0
    chart = TYPE_EFFECTIVENESS.get(attack_type, {})
    for defense_type in defense_types:
        multiplier *= chart.get(defense_type, 1.0)
    return multiplier


def _pokemon_weaknesses(defense_types):
    weak = []
    seen = set()
    for attack_type in TYPE_EFFECTIVENESS:
        multiplier = _type_multiplier(attack_type, defense_types)
        if multiplier > 1:
            seen.add(attack_type)
            weak.append((multiplier, attack_type))
    weak.sort(key=lambda item: (item[0], item[1]))
    return [f"{_title(t)} ({int(mult) if mult.is_integer() else mult}x)" for mult, t in weak]


def _pokemon_immunities(defense_types):
    immune = []
    for attack_type in TYPE_EFFECTIVENESS:
        multiplier = _type_multiplier(attack_type, defense_types)
        if multiplier == 0:
            immune.append(attack_type)
    immune.sort()
    return [f"{_title(t)} (0x)" for t in immune]


def format_response(kind, data, max_rows=30):
    if not data:
        return "No data found."

    if kind == "ability":
        return f"{_title(_row_value(data, 'name'))} ({_row_value(data, 'generation', '?')}):\n{_row_value(data, 'effect') or _row_value(data, 'short_effect') or 'No effect text.'}"

    if kind == "pokemon":
        types = [_row_value(data, 'type1'), _row_value(data, 'type2')] if _row_value(data, 'type2') else [_row_value(data, 'type1')]
        hidden_ability = _row_value(data, 'hidden_ability')
        hidden_key = str(hidden_ability).strip().lower() if hidden_ability else None
        seen = set()
        regular_ability_names = []
        for ability in [_row_value(data, 'ability_1'), _row_value(data, 'ability_2')]:
            if not ability:
                continue
            key = str(ability).strip().lower()
            if hidden_key and key == hidden_key:
                continue
            if key in seen:
                continue
            seen.add(key)
            regular_ability_names.append(_title(ability))
        regular_abilities = ", ".join(regular_ability_names)
        weaknesses = _pokemon_weaknesses([t for t in types if t])
        immunities = _pokemon_immunities([t for t in types if t])
        stats = (
            f"HP {_row_value(data, 'hp','?')}, Atk {_row_value(data, 'attack','?')}, Def {_row_value(data, 'defense','?')}, "
            f"SpA {_row_value(data, 'sp_attack','?')}, SpD {_row_value(data, 'sp_defense','?')}, Spe {_row_value(data, 'speed','?')}"
        )
        lines = [
            f"{_title(_row_value(data, 'name'))}",
            f"Types: {', '.join([_title(t) for t in types if t])}",
        ]
        generation = _row_value(data, 'generation')
        if generation:
            lines.append(f"Origin: {_format_generation(generation)}")
        lines.extend([
            f"Weaknesses: {', '.join(weaknesses) if weaknesses else 'None'}",
        ])
        if immunities:
            lines.append(f"Immunities: {', '.join(immunities)}")
        lines.append(f"Abilities: {regular_abilities or 'Unknown'}")
        if hidden_ability:
            lines.append(f"Hidden Abilities: {_title(hidden_ability)}")
        lines.extend([
            f"Base experience: {_row_value(data, 'base_experience','N/A')}",
            f"Height: {_row_value(data, 'height','N/A')} | Weight: {_row_value(data, 'weight','N/A')}",
            f"Stats: {stats}",
        ])
        return (
            "\n".join(lines)
        )

    if kind == "move":
        move_name = _title(_normalize_move_name(_row_value(data, 'name')))
        move_tag = _move_label_line(_row_value(data, 'name'))
        lines = [
            f"{move_name} ({_title(_row_value(data, 'type','unknown'))} {_title(_row_value(data, 'category','unknown'))})",
        ]
        if move_tag:
            lines.append(move_tag)
        lines.extend([
            f"Power: {_row_value(data, 'power','—')} | Accuracy: {_row_value(data, 'accuracy','—')} | PP: {_row_value(data, 'pp','—')}",
            f"Effect: {_row_value(data, 'effect') or 'No effect text.'}",
        ])
        return "\n".join(lines)

    if kind == "item":
        lines = [f"{_title(_row_value(data, 'name'))}"]
        category = _row_value(data, 'category')
        if category:
            lines.append(f"Category: {_title(str(category).replace('-', ' '))}")
        cost = _row_value(data, 'cost')
        if cost is not None:
            lines.append(f"Cost: {cost}")
        lines.append(f"Effect: {_row_value(data, 'effect') or _row_value(data, 'short_effect') or 'No effect text.'}")
        return "\n".join(lines)

    if kind == "route":
        rows = data if isinstance(data, list) else [data]
        lines = []
        current_group = None
        for r in rows:
            game = _title(_row_value(r, 'game'))
            route = _title(_row_value(r, 'route'))
            location = _title(_row_value(r, 'location_name'))
            pokemon = _title(_row_value(r, 'pokemon'))
            chance = _row_value(r, 'chance','?')
            method = _row_value(r, 'method') or 'unknown'
            min_level = _row_value(r, 'min_level') if _row_value(r, 'min_level') is not None else '?'
            max_level = _row_value(r, 'max_level') if _row_value(r, 'max_level') is not None else '?'
            heading = f"{game} — {route or location}"
            if heading != current_group:
                current_group = heading
                title_line = heading
                if route and location and route.lower() != location.lower():
                    title_line += f" ({location})"
                lines.append(title_line)
            lines.append(f"  {pokemon}: {chance}% {method} {min_level}-{max_level}")
        return "\n".join(lines)

    if kind == "egg_group":
        if isinstance(data, dict):
            if data.get('type') == 'group':
                return f"Egg group: {data['name'].title()}\nPokemon: {', '.join([p.title() for p in data['pokemon']])}"
            return f"Egg groups for {data['pokemon'].title()}: {', '.join([g.title() for g in data['egg_groups']])}"
        if isinstance(data, list):
            return ", ".join([_title(_row_value(row, 'egg_group')) for row in data])
        return str(data)

    if kind == "location":
        rows = data if isinstance(data, list) else [data]
        lines = []
        for r in rows[:max_rows]:
            method = _row_value(r, 'method') or 'unknown'
            min_level = _row_value(r, 'min_level') if _row_value(r, 'min_level') is not None else '?'
            max_level = _row_value(r, 'max_level') if _row_value(r, 'max_level') is not None else '?'
            lines.append(
                f"{_title(_row_value(r, 'location_name'))} — {_title(_row_value(r, 'pokemon'))} ({_title(_row_value(r, 'game'))}) {_row_value(r, 'chance','?')}% {method} {min_level}-{max_level}"
            )
        if len(rows) > max_rows:
            lines.append(f"... {len(rows) - max_rows} more results")
        return "\n".join(lines)

    if kind == "gyms":
        return "\n".join(
            f"{_row_value(row, 'gym_number','?')}. {_title(_row_value(row, 'city'))} — {_title(_row_value(row, 'leader'))} ({_title(_row_value(row, 'type'))})" for row in data
        )

    return str(data)
