import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.router import parse


class TestRouterIntentExtraction(unittest.TestCase):
    def test_conversational_route_queries(self):
        cases = [
            (
                "what are the encounters for route 12 in pokemon platinum",
                "route",
                {"route": "12", "game": "platinum"},
            ),
            (
                "route 201 platinum encounters",
                "route",
                {"route": "201", "game": "platinum"},
            ),
            (
                "encounters on route 7 in black 2",
                "route",
                {"route": "7", "game": "black 2"},
            ),
            (
                "show me route 10 in heartgold",
                "route",
                {"route": "10", "game": "heart gold"},
            ),
            (
                "what routes are in pokemon emerald",
                "route",
                {"game": "emerald"},
            ),
            (
                "route 5 in fire red",
                "route",
                {"route": "5", "game": "firered"},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_conversational_gym_queries(self):
        cases = [
            (
                "whats the first gym leader in pokemon sapphire",
                "gym",
                {"number": 1, "game": "sapphire"},
            ),
            (
                "who is gym 8 in soul silver",
                "gym",
                {"number": 8, "game": "soul silver"},
            ),
            (
                "3rd gym in alpha sapphire",
                "gym",
                {"number": 3, "game": "alpha sapphire"},
            ),
            (
                "badge from gym 4 in white 2",
                "gym",
                {"number": 4, "game": "white 2"},
            ),
            (
                "second gym in firered",
                "gym",
                {"number": 2, "game": "firered"},
            ),
            (
                "7th gym leader in heart gold",
                "gym",
                {"number": 7, "game": "heart gold"},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_ability_and_move_queries(self):
        cases = [
            ("what does mold breaker do", "ability", "mold breaker"),
            ("ability pressure", "ability", "pressure"),
            ("effect of levitate", "ability", "levitate"),
            ("tell me about thunderbolt move", "move", "thunderbolt"),
            ("power of ice beam move", "move", "ice beam"),
            ("move flamethrower", "move", "flamethrower"),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_pokemon_queries(self):
        cases = [
            ("pokemon pikachu", "pokemon", "pikachu"),
            ("tell me about garchomp", "pokemon", "garchomp"),
            ("charizard info", "pokemon", "charizard"),
            ("ability of gyarados", "pokemon", "gyarados"),
            ("what abilities does gyarados have", "pokemon", "gyarados"),
            ("mega swampert", "pokemon", "mega swampert"),
            ("alolan raichu", "pokemon", "alolan raichu"),
            ("hisuian zoroark", "pokemon", "hisuian zoroark"),
            ("paldean tauros", "pokemon", "paldean tauros"),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_location_queries(self):
        cases = [
            (
                "where can i catch dratini in pokemon crystal",
                "location",
                {"pokemon": "dratini", "game": "crystal"},
            ),
            (
                "what pokemon are found in viridian forest in pokemon yellow",
                "location",
                {"location": "viridian forest", "game": "yellow"},
            ),
            (
                "encounters in mt moon in fire red",
                "location",
                {"location": "mt moon", "game": "firered"},
            ),
            (
                "where do pokemon appear in bell tower in crystal",
                "location",
                {"location": "bell tower", "game": "crystal"},
            ),
            (
                "wild pokemon in eterna forest in platinum",
                "location",
                {"location": "eterna forest", "game": "platinum"},
            ),
            (
                "where can I find pidgey in fire red",
                "location",
                {"pokemon": "pidgey", "game": "firered"},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_location_game_no_encounters_message(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("what pokemon are in viridian forest in pokemon crystal")
        self.assertIn("There are no Pokemon encounters for Viridian Forest in Crystal.", response)

    def test_exact_route_matches_do_not_bleed(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("route 2 fire red")
        self.assertIn("Route 2", response)
        self.assertNotIn("Route 25", response)

    def test_pokemon_encounter_lookup_returns_routes_only(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("where can I find pidgey in red")
        self.assertIn("Pidgey encounters in Red", response)
        self.assertIn("Kanto Route 1 (Red) - Walk 50%", response)
        self.assertIn("Kanto Route 2 (Red) - Walk 45%", response)
        self.assertIn("Kanto Sea Route 21 (Red) - Walk 30%", response)

        magikarp_response, _ = handle_query_with_context("where can I find magikarp in red")
        self.assertIn("Kanto Route 12 (Red) - Old Rod 100%, Super Rod 25%", magikarp_response)
        self.assertIn("Fuchsia City (Red) - Old Rod 100%, Super Rod 25%", magikarp_response)

        dratini_response, _ = handle_query_with_context("where can I find dratini in crystal")
        self.assertIn("Dragons Den (Crystal) - Gift 100%, Super Rod 30%, Good Rod 10%, Surf 10%", dratini_response)
        self.assertIn("Johto Route 45 (Crystal) - Super Rod 30%, Good Rod 10%", dratini_response)
        self.assertNotIn("150%", dratini_response)

    def test_egg_and_tmhm_queries(self):
        cases = [
            (
                "what egg groups does eevee have",
                "egg",
                {"pokemon": "eevee"},
            ),
            (
                "which pokemon are in field egg group",
                "egg",
                {"group": "field"},
            ),
            (
                "egg groups for charizard",
                "egg",
                {"pokemon": "charizard"},
            ),
            (
                "tm26 in pokemon platinum",
                "tmhm",
                {"code": "tm26", "game": "platinum"},
            ),
            (
                "hm01 in soul silver",
                "tmhm",
                {"code": "hm01", "game": "soul silver"},
            ),
            (
                "tm100",
                "tmhm",
                {"code": "tm100", "game": None},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_item_and_crafting_queries(self):
        cases = [
            (
                "how do i make a fast ball",
                "item",
                {"name": "fast ball", "action": "craft", "game": None},
            ),
            (
                "how do you craft a friend ball",
                "item",
                {"name": "friend ball", "action": "craft", "game": None},
            ),
            (
                "fast ball recipe in pokemon heart gold",
                "item",
                {"name": "fast ball", "action": "craft", "game": "heart gold"},
            ),
            (
                "what does max potion do",
                "item",
                {"name": "max potion", "action": "lookup", "game": None},
            ),
            (
                "item leftovers",
                "item",
                {"name": "leftovers", "action": "lookup", "game": None},
            ),
            (
                "how do i make an ultra ball",
                "item",
                {"name": "ultra ball", "action": "craft", "game": None},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_move_learnset_queries_parse(self):
        cases = [
            (
                "what moves can mudkip pokemon learn",
                "pokemon_moves",
                {"pokemon": "mudkip", "game": None, "generation": None},
            ),
            (
                "what moves does mudkip learn in alpha sapphire",
                "pokemon_moves",
                {"pokemon": "mudkip", "game": "alpha sapphire", "generation": None},
            ),
            (
                "what pokemon can learn the move surf",
                "move_learners",
                {"move": "surf", "game": None, "generation": None},
            ),
            (
                "what pokemon learn bite",
                "move_learners",
                {"move": "bite", "game": None, "generation": None},
            ),
            (
                "what pokemon learn body slam",
                "move_learners",
                {"move": "body slam", "game": None, "generation": None},
            ),
            (
                "what pokemon can learn flamethrower in omega ruby",
                "move_learners",
                {"move": "flamethrower", "game": "omega ruby", "generation": None},
            ),
            (
                "what pokemon can learn bite in gen 2",
                "move_learners",
                {"move": "bite", "game": None, "generation": "generation ii"},
            ),
            (
                "what pokemon can have flame body in gen 3",
                "ability_learners",
                {"ability": "flame body", "game": None, "generation": "generation iii"},
            ),
            (
                "what pokemon can have no guard in scarlet",
                "ability_learners",
                {"ability": "no guard", "game": "scarlet", "generation": None},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_breeding_queries_parse(self):
        cases = [
            (
                "give me breeding info on mudkip pokemon",
                "breeding",
                {"pokemon": "mudkip", "game": None, "generation": None, "field": "all"},
            ),
            (
                "whats magbys breeding data in pokemon silver",
                "breeding",
                {"pokemon": "magbys", "game": "silver", "generation": None, "field": "all"},
            ),
            (
                "whats the gender rate for vullaby",
                "breeding",
                {"pokemon": "vullaby", "game": None, "generation": None, "field": "gender"},
            ),
            (
                "mudkip gender rates",
                "breeding",
                {"pokemon": "mudkip", "game": None, "generation": None, "field": "gender"},
            ),
            (
                "how many steps does it take to hatch a dratini egg in soul silver",
                "breeding",
                {"pokemon": "dratini", "game": "soul silver", "generation": None, "field": "steps"},
            ),
            (
                "mudkip egg steps",
                "breeding",
                {"pokemon": "mudkip", "game": None, "generation": None, "field": "cycles"},
            ),
            (
                "what pokemon have water 1 egg group in sun",
                "egg",
                {"group": "water 1", "game": "sun"},
            ),
            (
                "pokemon with bug egg group in pearl",
                "egg",
                {"group": "bug", "game": "pearl"},
            ),
            (
                "water 1",
                "egg",
                {"group": "water 1"},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_pokemon_game_queries_parse(self):
        cases = [
            (
                "beldum games?",
                "pokemon_games",
                {"pokemon": "beldum"},
            ),
            (
                "what games is beldum in?",
                "pokemon_games",
                {"pokemon": "beldum"},
            ),
            (
                "what games can you catch beldum in?",
                "pokemon_catch_games",
                {"pokemon": "beldum"},
            ),
            (
                "is beldum in silver",
                "pokemon_presence",
                {"pokemon": "beldum", "game": "silver"},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_pokemon_game_queries_response(self):
        from core.assistant import handle_query_with_context

        support_text, _ = handle_query_with_context("what games is beldum in?")
        catch_text, _ = handle_query_with_context("what games can you catch beldum in?")

        self.assertIn("Mainline games with Beldum support:", support_text)
        self.assertIn("Mainline games where Beldum can be caught in the wild:", catch_text)
        self.assertNotIn("Colosseum", support_text)

        no_text, _ = handle_query_with_context("is beldum in silver")
        yes_trade_text, _ = handle_query_with_context("is beldum in x")
        yes_enc_text, _ = handle_query_with_context("is beldum in omega ruby")
        self.assertIn("No, Beldum is not in Silver.", no_text)
        self.assertIn("Yes, but only if you trade/migrate", yes_trade_text)
        self.assertIn("Yes, Beldum is in Omega Ruby.", yes_enc_text)

    def test_multi_filter_queries_parse(self):
        cases = [
            (
                "what pokemon can learn surf and fly in emerald",
                "multi_filter",
                {"query": "what pokemon can learn surf and fly", "game": "emerald"},
            ),
            (
                "what pokemon are in the water 2 egg group and can learn hydro pump?",
                "multi_filter",
                {"query": "what pokemon are in the water 2 egg group and can learn hydro pump", "game": None},
            ),
            (
                "what electric type pokemon can learn flash cannon?",
                "multi_filter",
                {"query": "what electric type pokemon can learn flash cannon", "game": None},
            ),
            (
                "water 1 pokemon that can learn surf",
                "multi_filter",
                {"query": "water 1 pokemon that can learn surf", "game": None},
            ),
        ]
        for text, expected_intent, expected_entity in cases:
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertEqual(parsed["intent"], expected_intent)
                self.assertEqual(parsed["entity"], expected_entity)

    def test_multi_filter_queries_response(self):
        from core.assistant import handle_query_with_context

        text, _ = handle_query_with_context("what pokemon can learn surf and fly in emerald")
        self.assertIn("Pokemon matching qualifiers in Emerald", text)
        self.assertNotIn("- ", text)

        none_text, _ = handle_query_with_context("what pokemon are in the no eggs egg group and can learn hydro pump")
        self.assertIn("There aren't any pokemon.", none_text)

        none_ability_text, _ = handle_query_with_context("pokemon that can learn entrainment and have rks system")
        self.assertIn("There aren't any pokemon.", none_ability_text)

        typo_text, _ = handle_query_with_context("pokemon with water bubble that can lurn surf")
        self.assertIn("Araquanid", typo_text)

    def test_effect_queries_are_consistent_and_no_followup_prompt(self):
        from core.assistant import handle_query_with_context, handle_followup

        kings_plain, _ = handle_query_with_context("kings rock")
        kings_what, _ = handle_query_with_context("what does kings rock do")
        kings_item, kings_ctx = handle_query_with_context("what does the item kings rock do")
        self.assertEqual(kings_plain, kings_what)
        self.assertEqual(kings_what, kings_item)
        self.assertIn("Would you like", kings_item)

        more_text, _ = handle_followup(kings_ctx, "yes")
        self.assertIn("More:\n", more_text)
        self.assertIn("\n\n", more_text)

        wonder_plain, _ = handle_query_with_context("wonder guard")
        wonder_what, _ = handle_query_with_context("what does wonder guard do")
        self.assertEqual(wonder_plain, wonder_what)
        self.assertIn("Would you like", wonder_what)

        flamethrower_plain, _ = handle_query_with_context("flamethrower")
        flamethrower_what, _ = handle_query_with_context("what does flamethrower do")
        self.assertEqual(flamethrower_plain, flamethrower_what)
        self.assertNotIn("Would you like", flamethrower_what)

        intimidate_plain, _ = handle_query_with_context("intimidate")
        intimidate_what, _ = handle_query_with_context("what does intimidate do")
        self.assertEqual(intimidate_plain, intimidate_what)
        self.assertIn("Intimidate", intimidate_plain)

    def test_intimidate_parsing_not_corrupted(self):
        parsed = parse("what does intimidate do")
        self.assertEqual(parsed["intent"], "ability")
        self.assertEqual(parsed["entity"], "intimidate")

    def test_move_special_labels_and_name_normalization(self):
        from core.assistant import handle_query_with_context

        z_move, _ = handle_query_with_context("acid downpour physical")
        self.assertIn("(Z-Move)", z_move)
        self.assertIn("Acid Downpour Physical", z_move.split("\n", 1)[0])
        self.assertNotIn("  Physical", z_move)

        g_move, _ = handle_query_with_context("max flare")
        self.assertIn("(G-Move)", g_move)

        regular_move, _ = handle_query_with_context("flamethrower")
        self.assertNotIn("(Z-Move)", regular_move)
        self.assertNotIn("(G-Move)", regular_move)

    def test_unknown_query(self):
        parsed = parse("hello there")
        self.assertEqual(parsed["intent"], "unknown")
        self.assertEqual(parsed["entity"], "hello there")

    def test_pokemon_response_includes_evolution_tree(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("marshtomp")
        self.assertIn("Evolution Tree:", response)
        self.assertIn("Mudkip", response)
        self.assertIn("(Level 16)", response)
        self.assertIn("Marshtomp", response)
        self.assertIn("(Level 36)", response)
        self.assertIn("Swampert", response)

    def test_hisui_pokemon_response_includes_form_tree(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("hisuian zoroark")
        self.assertIn("Evolution Tree:", response)
        self.assertIn("Hisui Zorua", response)
        self.assertIn("(Level 30 In Legends Arceus)", response)
        self.assertIn("Hisui Zoroark", response)

    def test_branching_evolution_tree_shows_all_branches(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("eevee")
        self.assertIn("Evolution Tree:", response)
        self.assertIn("Eevee", response)
        self.assertIn("Vaporeon", response)
        self.assertIn("Jolteon", response)
        self.assertIn("Flareon", response)
        self.assertIn("Espeon", response)
        self.assertIn("Umbreon", response)
        self.assertIn("Leafeon", response)
        self.assertIn("Glaceon", response)
        self.assertIn("Sylveon", response)

    def test_toxel_tree_includes_both_toxtricity_forms(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("toxel")
        self.assertIn("Evolution Tree:", response)
        self.assertIn("Toxel", response)
        self.assertIn("(Level 30, Amped Nature)", response)
        self.assertIn("Toxtricity Amped", response)
        self.assertIn("(Level 30, Low Key Nature)", response)
        self.assertIn("Toxtricity Low Key", response)

    def test_other_form_split_evolution_trees(self):
        from core.assistant import handle_query_with_context

        rockruff_response, _ = handle_query_with_context("rockruff")
        self.assertIn("(Level 25 at day)", rockruff_response)
        self.assertIn("Lycanroc Midday", rockruff_response)
        self.assertIn("(Level 25 at night)", rockruff_response)
        self.assertIn("Lycanroc Midnight", rockruff_response)
        self.assertIn("(Level 25 at dusk)", rockruff_response)
        self.assertIn("Lycanroc Dusk", rockruff_response)

        kubfu_response, _ = handle_query_with_context("kubfu")
        self.assertIn("Urshifu Single Strike", kubfu_response)
        self.assertIn("Urshifu Rapid Strike", kubfu_response)

        pumpkaboo_response, _ = handle_query_with_context("pumpkaboo small")
        self.assertIn("Pumpkaboo Small", pumpkaboo_response)
        self.assertIn("(Trade)", pumpkaboo_response)
        self.assertIn("Gourgeist Small", pumpkaboo_response)

        espurr_response, _ = handle_query_with_context("espurr")
        self.assertIn("Meowstic Male", espurr_response)
        self.assertIn("Meowstic Female", espurr_response)

        lechonk_response, _ = handle_query_with_context("lechonk")
        self.assertIn("Oinkologne Male", lechonk_response)
        self.assertIn("Oinkologne Female", lechonk_response)

    def test_regional_tree_only_labels_existing_form_stages(self):
        from core.assistant import handle_query_with_context

        alolan_response, _ = handle_query_with_context("alolan raichu")
        self.assertIn("Pichu", alolan_response)
        self.assertIn("Pikachu", alolan_response)
        self.assertIn("Alolan Raichu", alolan_response)
        self.assertNotIn("Alolan Pichu", alolan_response)
        self.assertNotIn("Alolan Pikachu", alolan_response)

        galar_response, _ = handle_query_with_context("galarian meowth")
        self.assertIn("Galarian Meowth", galar_response)
        self.assertIn("Persian", galar_response)
        self.assertNotIn("Galarian Persian", galar_response)

    def test_trade_evolution_includes_item_requirement(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("steelix")
        self.assertIn("Evolution Tree:", response)
        self.assertIn("Onix", response)
        self.assertIn("Trade with Metal Coat", response)
        self.assertIn("Steelix", response)

    def test_pokemon_weaknesses_list_2x_before_4x(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("charizard")
        weaknesses_line = next(line for line in response.splitlines() if line.startswith("Weaknesses:"))
        self.assertIn("Electric (2x)", weaknesses_line)
        self.assertIn("Rock (4x)", weaknesses_line)
        self.assertLess(weaknesses_line.index("Electric (2x)"), weaknesses_line.index("Rock (4x)"))

    def test_pokemon_type_immunities_are_listed_only_when_present(self):
        from core.assistant import handle_query_with_context

        gengar_response, _ = handle_query_with_context("gengar")
        self.assertIn("Immunities:", gengar_response)
        gengar_line = next(line for line in gengar_response.splitlines() if line.startswith("Immunities:"))
        self.assertIn("Normal (0x)", gengar_line)
        self.assertIn("Fighting (0x)", gengar_line)

        electrode_response, _ = handle_query_with_context("electrode")
        self.assertNotIn("Immunities:", electrode_response)

    def test_unknown_lookup_prefers_pokemon_over_location_name_match(self):
        from core.assistant import handle_query_with_context

        response, _ = handle_query_with_context("diglett")
        self.assertTrue(response.startswith("Diglett\n"))
        self.assertIn("Types:", response)
        self.assertNotIn("Digletts Cave", response)


if __name__ == "__main__":
    unittest.main()
