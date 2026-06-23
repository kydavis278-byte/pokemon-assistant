import re


GAME_ALIASES = {
    "red": "red",
    "blue": "blue",
    "yellow": "yellow",
    "green": "green",
    "gold": "gold",
    "silver": "silver",
    "crystal": "crystal",
    "ruby": "ruby",
    "sapphire": "sapphire",
    "emerald": "emerald",
    "fire red": "firered",
    "firered": "firered",
    "leaf green": "leafgreen",
    "leafgreen": "leafgreen",
    "diamond": "diamond",
    "pearl": "pearl",
    "platinum": "platinum",
    "heart gold": "heart gold",
    "heartgold": "heart gold",
    "soul silver": "soul silver",
    "soulsilver": "soul silver",
    "black": "black",
    "white": "white",
    "black 2": "black 2",
    "black2": "black 2",
    "white 2": "white 2",
    "white2": "white 2",
    "x": "x",
    "y": "y",
    "omega ruby": "omega ruby",
    "omegaruby": "omega ruby",
    "alpha sapphire": "alpha sapphire",
    "alphasapphire": "alpha sapphire",
    "sun": "sun",
    "moon": "moon",
    "ultra sun": "ultra sun",
    "ultrasun": "ultra sun",
    "ultra moon": "ultra moon",
    "ultramoon": "ultra moon",
    "sword": "sword",
    "shield": "shield",
    "brilliant diamond": "brilliant diamond",
    "shining pearl": "shining pearl",
    "legends arceus": "legends arceus",
    "scarlet": "scarlet",
    "violet": "violet",
}

GAME_PATTERNS = sorted(GAME_ALIASES.keys(), key=len, reverse=True)

ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
}

GENERATION_MAP = {
    "1": "generation i",
    "2": "generation ii",
    "3": "generation iii",
    "4": "generation iv",
    "5": "generation v",
    "6": "generation vi",
    "7": "generation vii",
    "8": "generation viii",
    "9": "generation ix",
    "i": "generation i",
    "ii": "generation ii",
    "iii": "generation iii",
    "iv": "generation iv",
    "v": "generation v",
    "vi": "generation vi",
    "vii": "generation vii",
    "viii": "generation viii",
    "ix": "generation ix",
}

KNOWN_EGG_GROUPS = {
    "monster",
    "bug",
    "flying",
    "field",
    "fairy",
    "grass",
    "human shape",
    "human-shaped",
    "humanlike",
    "humanshape",
    "water 1",
    "water1",
    "water 2",
    "water2",
    "water 3",
    "water3",
    "mineral",
    "amorphous",
    "water 2",
    "ditto",
    "dragon",
    "no eggs",
    "no-eggs",
    "normal",
}


def _looks_like_egg_group_query(text):
    cleaned = (text or "").strip().lower().replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in KNOWN_EGG_GROUPS:
        return True
    cleaned_no_space = cleaned.replace(" ", "")
    return cleaned_no_space in {"water1", "water2", "water3", "humanshape", "noeggs"}


def normalize(text):
    t = text.lower().strip()
    t = t.replace("pokémon", "pokemon")
    t = re.sub(r"\bwhat's\b", "what is", t)
    t = re.sub(r"\bwhats\b", "what is", t)
    t = re.sub(r"\bwho's\b", "who is", t)
    t = re.sub(r"\bwheres\b", "where is", t)
    t = re.sub(r"\bwhere's\b", "where is", t)
    t = re.sub(r"\bim\b", "i am", t)
    t = re.sub(r"\blurn\b", "learn", t)
    t = re.sub(r"\bmoldbreaker\b", "mold breaker", t)
    t = re.sub(r"[\u2018\u2019\u201c\u201d'\"?!.,]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _extract_game(text, allow_tail=True):
    for candidate in GAME_PATTERNS:
        match = re.search(rf"\b{re.escape(candidate)}\b", text)
        if not match:
            continue
        canonical = GAME_ALIASES[candidate]
        remaining = (text[:match.start()] + " " + text[match.end():]).strip()
        remaining = re.sub(r"\s+", " ", remaining)
        return canonical, remaining

    if allow_tail:
        tail = re.search(r"(?:in\s+pokemon|for\s+pokemon|in|for)\s+([a-z0-9 ]+)$", text)
        if tail:
            guess = tail.group(1).strip()
            canonical = GAME_ALIASES.get(guess, guess)
            remaining = text[:tail.start()].strip()
            return canonical, remaining

    return None, text


def _extract_generation(text):
    match = re.search(r"\b(?:gen|generation)\s*([1-9]|ix|viii|vii|vi|iv|v|iii|ii|i)\b", text)
    if not match:
        return None, text
    token = match.group(1).lower()
    generation = GENERATION_MAP.get(token)
    remaining = (text[:match.start()] + " " + text[match.end():]).strip()
    remaining = re.sub(r"\s+", " ", remaining)
    return generation, remaining


def _extract_route_number(text):
    match = re.search(r"\broute\s*([0-9]{1,3}[a-z]?)\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b([0-9]{1,3}[a-z]?)\s*route\b", text)
    if match:
        return match.group(1)
    return None


def _extract_encounter_pokemon(text):
    prefixes = [
        r"where can i find",
        r"where do i find",
        r"where can i catch",
        r"where do i catch",
        r"where can i encounter",
        r"where do i encounter",
    ]
    prefix_pattern = "|".join(prefixes)
    match = re.search(rf"^(?:{prefix_pattern})\s+(.+)$", text)
    if not match:
        return None
    pokemon = match.group(1).strip()
    pokemon = re.sub(r"^(?:a|an|the)\s+", "", pokemon).strip()
    pokemon = re.sub(r"\b(?:in|on|at|for|from)\s*$", "", pokemon).strip()
    pokemon = re.sub(r"\b(?:in|on|at|for|from)\s+(?:pokemon\s+)?[a-z0-9 ]+$", "", pokemon).strip()
    pokemon = re.sub(r"\b(pokemon|game|version)\b", "", pokemon).strip()
    pokemon = re.sub(r"\s+", " ", pokemon)
    return pokemon or None


def _extract_gym_number(text):
    match = re.search(r"\bgym\s*([0-9]{1,2})\b", text)
    if match:
        return int(match.group(1))

    match = re.search(r"\b([0-9]{1,2})(?:st|nd|rd|th)?\s+gym\b", text)
    if match:
        return int(match.group(1))

    for word, value in ORDINAL_WORDS.items():
        if re.search(rf"\b{word}\b", text) and ("gym" in text or "leader" in text or "badge" in text):
            return value
    return None


def score_intents(text):
    scores = {
        "ability": 0,
        "pokemon": 0,
        "move": 0,
        "multi_filter": 0,
        "pokemon_moves": 0,
        "move_learners": 0,
        "ability_learners": 0,
        "pokemon_presence": 0,
        "pokemon_games": 0,
        "pokemon_catch_games": 0,
        "breeding": 0,
        "item": 0,
        "location": 0,
        "route": 0,
        "gym": 0,
        "egg": 0,
        "tmhm": 0,
        "unknown": 0,
    }

    item_keyword_match = re.search(r"\b(item|items|potion|revive|elixir|ball|berry|repel|incense|amulet|stone|plate|orb|band|scarf|leftovers)\b", text)

    pokemon_moves_match = bool(re.search(r"\bwhat moves (?:can|does) .+ learn\b", text))
    move_learners_match = bool(re.search(r"\bwhat pokemon (?:can )?learn (?:the )?(?:move )?.+\b", text))
    ability_learners_match = bool(re.search(r"\bwhat pokemon (?:can )?(?:have|has|get) .+\b", text)) and not bool(re.search(r"\begg groups?\b", text))

    if pokemon_moves_match:
        scores["pokemon_moves"] += 10
    if move_learners_match:
        scores["move_learners"] += 10
    if ability_learners_match:
        scores["ability_learners"] += 10

    catch_games_match = bool(
        re.search(r"\bwhat games (?:can you|can i|can we)?\s*catch\s+.+\s+in\b", text)
        or re.search(r"\bwhat games is\s+.+\s+catchable in\b", text)
    )
    if catch_games_match:
        scores["pokemon_catch_games"] += 12

    supported_games_match = bool(
        re.search(r"\bwhat games (?:is|are)\s+.+\s+in\b", text)
        or re.search(r"\b[a-z0-9\- ]+\s+games\b", text)
    )
    if supported_games_match and not catch_games_match:
        scores["pokemon_games"] += 9

    presence_match = bool(re.search(r"^is\s+.+\s+in\s+.+$", text))
    if presence_match:
        scores["pokemon_presence"] += 11

    has_learn = bool(re.search(r"\b(?:can\s+learn|learn)\b", text))
    has_multi_moves = bool(re.search(r"\b(?:can\s+learn|learn)\b.+\band\b.+", text))
    has_egg = "egg group" in text or "egg groups" in text
    has_egg_shorthand = bool(
        re.search(
            r"\b(?:water\s*[123]|no\s*eggs?|human\s*shape|humanshape|monster|dragon|field|mineral|amorphous|ditto|bug|fairy|grass)\s+pokemon\b",
            text,
        )
    )
    has_type = bool(re.search(r"\b(?:normal|fire|water|electric|grass|ice|fighting|poison|ground|flying|psychic|bug|rock|ghost|dragon|dark|steel|fairy)\s+type\b", text))
    has_ability_like = bool(re.search(r"\bwith\s+[a-z0-9 -]+\b", text)) and not has_egg or bool(re.search(r"\bcan\s+have\s+[a-z0-9 -]+\b", text))
    has_egg_intersection = has_egg and (bool(re.search(r"\bshare\b", text)) or bool(re.search(r"\band\b", text)))

    if "pokemon" in text and (
        (has_learn and (has_multi_moves or has_egg or has_egg_shorthand or has_type or has_ability_like))
        or (has_egg and has_type)
        or has_egg_intersection
    ):
        scores["multi_filter"] += 13
    if has_multi_moves and "pokemon" in text:
        scores["multi_filter"] += 6
    if has_egg_intersection and "pokemon" in text:
        scores["multi_filter"] += 5

    breeding_match = bool(re.search(r"\b(breeding info|breeding data|breeding|gender rates?|gender|egg cycles?|egg steps?|hatch|steps to hatch)\b", text))
    if breeding_match:
        scores["breeding"] += 10

    if "ability" in text or "abilities" in text or "effect" in text or "hidden ability" in text or (re.search(r"\bwhat does .+ do\b", text) and not item_keyword_match):
        scores["ability"] += 4
    if "move" in text or "power" in text or "accuracy" in text or "pp" in text or "learn" in text or "damage" in text:
        scores["move"] += 4
    if re.search(r"\b(?:tm|hm)\d{1,3}\b", text):
        scores["tmhm"] += 6
    if item_keyword_match:
        scores["item"] += 3
    if re.search(r"\bwhat does .+ do\b", text) and item_keyword_match:
        scores["item"] += 3
    if re.search(r"\b(craft|crafting|make|build|recipe|ingredients|how do i make|how do you make|how to make)\b", text):
        scores["item"] += 6
    if re.search(r"\b(encounter|encounters|found|spawn|catch|appear|where|location|forest|cave|tower|lake)\b", text):
        if "egg group" not in text and "egg groups" not in text:
            scores["location"] += 5
    if "route" in text or re.search(r"\bencounters?\s+(?:for|on|in)\s+route\b", text):
        if "what routes" in text or "all routes" in text or "routes in" in text or "list routes" in text or "route list" in text:
            scores["route"] += 4
        else:
            scores["route"] += 8
    if "gym" in text or "badge" in text or "leader" in text:
        scores["gym"] += 4
    if _extract_gym_number(text) is not None:
        scores["gym"] += 3
    if "egg group" in text or "egg groups" in text or _looks_like_egg_group_query(text):
        scores["egg"] += 5
    if re.search(r"\b(pokemon|pokedex|stats|base stats|tell me about|info on|information on|info)\b", text) and scores["location"] == 0 and scores["move"] == 0 and scores["ability"] == 0 and scores["egg"] == 0 and scores["route"] == 0 and scores["tmhm"] == 0 and scores["gym"] == 0 and scores["item"] == 0:
        scores["pokemon"] += 3

    # Form-prefixed names like "mega swampert" or "alolan raichu" are Pokemon lookups
    # even when users don't include the word "pokemon".
    if re.search(r"\b(mega|alolan|galarian|hisuian|paldean)\b", text) and scores["ability"] == 0 and scores["move"] == 0 and scores["location"] == 0 and scores["route"] == 0 and scores["egg"] == 0 and scores["tmhm"] == 0:
        scores["pokemon"] += 2

    if sum(scores.values()) == 0:
        scores["unknown"] = 1

    return scores


def get_intent(text):
    # Route natural pokemon-ability lookups to pokemon details, not ability encyclopedia.
    # Examples: "what abilities does gyarados have", "ability of charizard".
    if re.search(r"\bwhat\s+abilities\s+does\s+.+\s+have\b", text) or re.search(r"\bability\s+of\s+.+$", text) or re.search(r"\babilities\s+of\s+.+$", text):
        return "pokemon"

    scores = score_intents(text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def _strip_noise(text, noise):
    t = text
    for token in noise:
        t = re.sub(r"\b" + re.escape(token) + r"\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def get_entity(text, intent):
    if intent == "pokemon_presence":
        game, t = _extract_game(text, allow_tail=False)
        match = re.search(r"^is\s+(.+?)\s+in\b", text)
        pokemon_name = match.group(1).strip() if match else t
        pokemon_name = _strip_noise(pokemon_name, ["is", "pokemon", "the", "in"])
        return {
            "pokemon": pokemon_name,
            "game": game,
        }

    if intent == "multi_filter":
        game, t = _extract_game(text, allow_tail=False)
        t = re.sub(r"\b(in|for)\s*$", "", t).strip()
        return {
            "query": t.strip(),
            "game": game,
        }

    if intent == "pokemon_games":
        t = text
        match = re.search(r"\bwhat games (?:is|are)\s+(.+?)\s+in\b", t)
        if match:
            pokemon_name = match.group(1).strip()
        else:
            tail_match = re.search(r"^(.+?)\s+games\??$", t)
            pokemon_name = tail_match.group(1).strip() if tail_match else t
        pokemon_name = _strip_noise(pokemon_name, ["what", "games", "is", "are", "pokemon", "the", "in", "can", "you", "i", "we"])
        return {"pokemon": pokemon_name}

    if intent == "pokemon_catch_games":
        t = text
        match = re.search(r"\bwhat games (?:can you|can i|can we)?\s*catch\s+(.+?)\s+in\b", t)
        if match:
            pokemon_name = match.group(1).strip()
        else:
            match = re.search(r"\bwhat games is\s+(.+?)\s+catchable in\b", t)
            pokemon_name = match.group(1).strip() if match else t
        pokemon_name = _strip_noise(pokemon_name, ["what", "games", "can", "you", "i", "we", "catch", "is", "catchable", "in", "pokemon", "the"])
        return {"pokemon": pokemon_name}

    if intent == "pokemon_moves":
        generation, t = _extract_generation(text)
        game, t = _extract_game(t, allow_tail=False)
        match = re.search(r"\bwhat moves (?:can|does)\s+(.+?)\s+learn\b", t)
        pokemon_name = match.group(1).strip() if match else t
        pokemon_name = _strip_noise(pokemon_name, ["pokemon", "the", "a", "an"])
        return {
            "pokemon": pokemon_name,
            "game": game,
            "generation": generation,
        }

    if intent == "move_learners":
        generation, t = _extract_generation(text)
        game, t = _extract_game(t, allow_tail=False)
        match = re.search(r"\bwhat pokemon (?:can\s+)?learn\s+(?:the\s+)?(?:move\s+)?(.+)$", t)
        move_name = match.group(1).strip() if match else t
        move_name = _strip_noise(move_name, ["the", "move", "pokemon", "can", "learn", "in", "for"])
        return {
            "move": move_name,
            "game": game,
            "generation": generation,
        }

    if intent == "ability_learners":
        generation, t = _extract_generation(text)
        game, t = _extract_game(t, allow_tail=False)
        match = re.search(r"\bwhat pokemon (?:can\s+)?(?:have|has|get)\s+(.+)$", t)
        ability_name = match.group(1).strip() if match else t
        ability_name = _strip_noise(ability_name, ["the", "ability", "pokemon", "can", "have", "has", "get", "in", "for"])
        return {
            "ability": ability_name,
            "game": game,
            "generation": generation,
        }

    if intent == "ability":
        noise = ["what does", "what is", "the ability", "ability", "abilities", "do", "does", "tell me about", "show me", "describe", "effect of", "effect"]
        return _strip_noise(text, noise)

    if intent == "move":
        noise = ["what does", "what is", "the move", "move", "do", "does", "tell me about", "show me", "describe", "power of", "accuracy of", "pp of"]
        return _strip_noise(text, noise)

    if intent == "item":
        action = "craft" if re.search(r"\b(craft|crafting|make|build|recipe|ingredients|how do i make|how do you make|how to make)\b", text) else "lookup"
        game, t = _extract_game(text)
        t = re.sub(r"\b(how do i make|how do you make|how to make|how do i craft|how do you craft|craft|crafting|recipe|ingredients|what is|what are|what does|do|does|tell me about|show me|item|items|in pokemon)\b", "", t)
        t = _strip_noise(t, ["an", "a", "the", "for", "in", "pokemon"])
        return {
            "name": t.strip(),
            "action": action,
            "game": game,
        }

    if intent == "pokemon":
        t = text
        abilities_have_match = re.search(r"\bwhat\s+abilities\s+does\s+(.+?)\s+have\b", t)
        if abilities_have_match:
            return _strip_noise(abilities_have_match.group(1).strip(), ["the", "pokemon"])

        ability_of_match = re.search(r"\b(?:ability|abilities)\s+of\s+(.+)$", t)
        if ability_of_match:
            return _strip_noise(ability_of_match.group(1).strip(), ["the", "pokemon"])

        t = re.sub(r"what (?:is|are|does|do|about) ", "", t)
        t = t.replace("pokemon", "")
        game, t = _extract_game(t)
        _ = game
        return _strip_noise(t, ["in", "for", "on", "stats", "base stats", "information", "info", "about", "tell me", "show me"])

    if intent == "gym":
        t = text
        game, t = _extract_game(t)
        number = _extract_gym_number(t)
        if number is not None:
            return {"number": number, "game": game}

        # fallback: return cleaned text as before
        return _strip_noise(text, ["what", "are", "the", "gym", "gym leader", "in", "pokemon", "leader", "badge", "show", "where"])

    if intent == "egg":
        generation, text = _extract_generation(text)
        game, text = _extract_game(text, allow_tail=False)

        def _clean_group_text(value):
            g = (value or "").strip()
            g = re.sub(r"\begg groups?\b", "", g).strip()
            g = re.sub(r"\b(in|for)\s*$", "", g).strip()
            return re.sub(r"\s+", " ", g)

        def _clean_pokemon_text(value):
            p = (value or "").strip()
            p = re.sub(r"\b(in|for)\s*$", "", p).strip()
            return re.sub(r"\s+", " ", p)

        def _with_scope(base):
            if game:
                base["game"] = game
            if generation:
                base["generation"] = generation
            return base

        # "what egg groups does <pokemon> have?"
        pokemon_have_match = re.search(r"what egg groups (?:does|do) (?:the\s+)?(.+?) have\??$", text)
        if pokemon_have_match:
            return _with_scope({"pokemon": _clean_pokemon_text(pokemon_have_match.group(1).strip())})

        group_match = re.search(r"(?:which|what) pokemon (?:are |can be |have )?(?:in\s+)?(?:the\s+)?(.+?)(?: egg groups?| egg group)?$", text)
        if group_match:
            return _with_scope({"group": _clean_group_text(group_match.group(1).strip())})

        pokemon_with_group_match = re.search(r"(?:pokemon\s+with|pokemon\s+in)\s+(?:the\s+)?(.+?)(?:\s+egg groups?|\s+egg group)?$", text)
        if pokemon_with_group_match:
            return _with_scope({"group": _clean_group_text(pokemon_with_group_match.group(1).strip())})

        pokemon_match = re.search(r"egg groups? (?:for|of) (?:the )?(.+)$", text)
        if pokemon_match:
            return _with_scope({"pokemon": _clean_pokemon_text(pokemon_match.group(1).strip())})

        match = re.search(r"(?:for|in)\s+(?:the\s+)?(.+?)(?:\s+egg groups?)?$", text)
        if match:
            return _with_scope({"group": _clean_group_text(match.group(1).strip())})

        cleaned = _clean_group_text(_strip_noise(text, ["what are", "what is", "what", "tell me", "show me", "describe", "the", "egg groups", "egg group", "for", "in", "pokemon", "of", "list"]))
        return _with_scope({"group": cleaned}) if cleaned else {}

    if intent == "breeding":
        generation, t = _extract_generation(text)
        game, t = _extract_game(t, allow_tail=False)

        field = "all"
        if re.search(r"\begg groups?\b", t):
            field = "egg_groups"
        elif re.search(r"\bgender rates?\b|\bgender\b", t):
            field = "gender"
        elif re.search(r"\begg cycles?\b|\begg steps?\b", t):
            field = "cycles"
        elif re.search(r"\bsteps\b|\bhatch\b", t):
            field = "steps"

        m = re.search(r"(?:on|for|of)\s+(.+?)(?:\s+pokemon)?$", t)
        pokemon_name = m.group(1).strip() if m else t
        pokemon_name = _strip_noise(
            pokemon_name,
            ["give", "me", "breeding", "info", "data", "whats", "what", "is", "the", "of", "for", "on", "pokemon", "how", "many", "does", "it", "take", "to", "hatch", "a", "an", "egg", "rate", "rates", "groups", "group", "cycles", "steps", "gender"],
        )
        pokemon_name = re.sub(r"\b(in|for)\s*$", "", pokemon_name).strip()

        return {
            "pokemon": pokemon_name.strip(),
            "game": game,
            "generation": generation,
            "field": field,
        }

    if intent == "tmhm":
        tmhm_match = re.search(r"\b((?:tm|hm)\d{1,3})\b(?:\s+in\s+(?:pokemon\s+)?(.+))?$", text)
        if tmhm_match:
            game = tmhm_match.group(2).strip() if tmhm_match.group(2) else None
            if game:
                game = GAME_ALIASES.get(game, game)
            return {
                "code": tmhm_match.group(1).strip(),
                "game": game,
            }
        return {}

    if intent == "route":
        game, location = _extract_game(text)
        route_num = _extract_route_number(location)

        if not route_num:
            cleaned = re.sub(r"what (?:are|is|show|list|whats) ", "", location)
            cleaned = _strip_noise(cleaned, ["encounters", "encounter", "for", "on", "in", "pokemon", "route", "routes", "game", "show", "list", "what", "are", "is", "all", "the"])
            guess_match = re.search(r"\b([0-9]{1,3}[a-z]?)\b", cleaned)
            route_num = guess_match.group(1) if guess_match else cleaned.strip()

        if game:
            return {"route": route_num, "game": game} if route_num else {"game": game}
        return {"route": route_num, "game": None} if route_num else {}

    if intent == "location":
        game, location = _extract_game(text)

        pokemon = _extract_encounter_pokemon(location)
        if pokemon:
            return {
                "pokemon": pokemon,
                "game": game.strip() if game else None,
            }

        location = re.sub(r"^where is ", "", location)
        location = re.sub(r"what pokemon (?:are |can be )?(?:found|appear|live|are|on) in ", "", location)
        location = re.sub(r"in pokemon [a-z0-9 ]+$", "", location)
        location = re.sub(r"\b(pokemon|game|version)\b", "", location)
        location = re.sub(r"[^a-z0-9 ]", "", location)
        location = _strip_noise(location, ["what", "pokemon", "are", "found", "appear", "encounter", "encounters", "in", "on", "for", "the", "wild", "where", "can", "i", "catch", "do"])
        return {
            "location": location.strip(),
            "game": game.strip() if game else None,
        }

    return text.strip()


def parse(text):
    normalized = normalize(text)
    intent = get_intent(normalized)
    entity = get_entity(normalized, intent)
    return {
        "intent": intent,
        "entity": entity,
    }
