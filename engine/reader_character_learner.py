#!/usr/bin/env python3
"""17th-Node Player Character Engine & Autonomous Offline Arc Learner.

Implements:
1. 100% Clean-Slate Onboarding state (`initialized: False` until player configures Name & Aspects).
2. Continuous psychometric and relational learning from player margin comments, theories, and choices.
3. Autonomous 'Ghost-Pilot' offline evolution that advances the 17th Node's arc alongside the 16
   canonical characters when the player is away, using learned context and optional local Ollama.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

SQUAD_TO_DEFAULT_PROJECT: dict[str, str] = {
    "THE_FORGE": "project_02_first_forge",
    "THE_WILDS": "project_04_sanctuary",
    "THE_MIND": "project_07_simulacrum",
    "THE_HUB": "project_01_living_atlas",
    "DISCOVERY_ADAPTIVE": "project_01_living_atlas",
}

SQUAD_MENTOR_PAIRS: dict[str, tuple[str, str]] = {
    "THE_FORGE": ("enclave_03_silas", "enclave_04_leo"),
    "THE_WILDS": ("enclave_05_kaio", "enclave_07_willow"),
    "THE_MIND": ("enclave_10_isla", "enclave_11_kenna"),
    "THE_HUB": ("enclave_15_dorian", "enclave_14_vex"),
    "DISCOVERY_ADAPTIVE": ("enclave_15_dorian", "enclave_16_elara"),
}

CHARACTER_DISPLAY_NAMES: dict[str, str] = {
    "enclave_01_hector": "Hector",
    "enclave_02_jane": "Jane",
    "enclave_03_silas": "Silas",
    "enclave_04_leo": "Leo",
    "enclave_05_kaio": "Kaio",
    "enclave_06_zara": "Zara",
    "enclave_07_willow": "Willow",
    "enclave_08_terra": "Terra",
    "enclave_09_orion": "Orion",
    "enclave_10_isla": "Isla",
    "enclave_11_kenna": "Kenna",
    "enclave_12_elias": "Elias",
    "enclave_13_ryn": "Ryn",
    "enclave_14_vex": "Vex",
    "enclave_15_dorian": "Dorian",
    "enclave_16_elara": "Elara",
}

KEYWORD_LENS_WEIGHTS: dict[str, dict[str, float]] = {
    "analytical_forge": {
        "keywords": 1.0,
        "conscientiousness": 2.5,
        "openness": 1.0,
        "neuroticism": -1.5,
    },
    "exploratory_wilds": {
        "keywords": 1.0,
        "openness": 3.0,
        "extraversion": 1.5,
    },
    "empathetic_hub": {
        "keywords": 1.0,
        "agreeableness": 3.0,
        "extraversion": 1.0,
        "neuroticism": -1.0,
    },
    "witty_banter": {
        "keywords": 1.0,
        "extraversion": 2.5,
        "openness": 1.5,
        "agreeableness": 1.0,
    },
}

ANALYTICAL_WORDS = frozenset(
    {
        "alloy",
        "lattice",
        "voltage",
        "laser",
        "circuit",
        "entropy",
        "magnetic",
        "flux",
        "harmonic",
        "calibrate",
        "ferrofluid",
        "pressure",
        "torque",
        "vector",
        "theorem",
        "seal",
        "frequency",
    }
)
EXPLORATORY_WORDS = frozenset(
    {
        "mycelium",
        "fungus",
        "mushroom",
        "spore",
        "cavern",
        "aquifer",
        "bioluminescent",
        "signal",
        "syntax",
        "explore",
        "ridge",
        "canopy",
        "specimen",
        "ruin",
        "mystery",
        "echo",
    }
)
EMPATHETIC_WORDS = frozenset(
    {
        "family",
        "feast",
        "soup",
        "stew",
        "warmth",
        "trust",
        "sleep",
        "care",
        "together",
        "home",
        "shelter",
        "listen",
        "breathe",
        "heal",
        "heart",
        "safe",
    }
)
WITTY_WORDS = frozenset(
    {
        "sock",
        "retrograde",
        "cheese",
        "roast",
        "prank",
        "laugh",
        "absurd",
        "coffee",
        "spoon",
        "banter",
        "wrench",
        "crispy",
        "popcorn",
        "sarcasm",
        "joke",
    }
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_state_path(repo_root: Path | None = None) -> Path:
    xdg = os.environ.get("XDG_STATE_HOME", "").strip()
    base = Path(xdg) if xdg else (Path.home() / ".local" / "state")
    return base / "lfs-enclave-factory" / "player_node_17.json"


def create_clean_slate_17th_node() -> dict[str, Any]:
    """Return a 100% Clean-Slate uninitialized 17th-Node profile."""
    return {
        "schema_version": "enclave-17th-node-v1.0",
        "character_id": "enclave_17_player",
        "initialized": False,
        "onboarding_required": True,
        "created_at_iso": _utc_now_iso(),
        "updated_at_iso": _utc_now_iso(),
        "identity": {
            "name": "",
            "title": "The 17th Node",
            "pronouns": "they/them",
            "squad_affinity": "DISCOVERY_ADAPTIVE",
            "grand_project_id": "project_01_living_atlas",
            "cognitive_style": "ADAPTIVE_LEARNER",
            "signature_tool": "Hand-Ground Brass Resonance Slate",
            "genius_vs_mundane_quirk": "Can cross-index sixteen disciplinary telemetry streams at once, yet constantly misplaces their brass stylus in the arboretum moss.",
        },
        "psychometrics": {
            "big_five": {
                "openness": 50.0,
                "conscientiousness": 50.0,
                "extraversion": 50.0,
                "agreeableness": 50.0,
                "neuroticism": 50.0,
            },
            "inferred_mbti": "INTJ",
            "inferred_enneagram": "5w6",
            "vex_override_sign": "Sagittarius (The Audacious Improviser)",
            "dominant_lens": "Balanced Polymath",
        },
        "arc_progression": {
            "stage": "CLEAN_SLATE_ARRIVAL",
            "chapters_annotated": 0,
            "choices_made": 0,
            "autonomous_sols_advanced": 0,
            "the_question_pursued": "What hidden harmonic law binds the sixteen specialists and the planet's core?",
            "learned_voice_traits": [
                "Observant",
                "Tactically calm under pressure",
                "Dryly humorous",
            ],
        },
        "bonds_with_16": {
            cid: {
                "character_id": cid,
                "name": CHARACTER_DISPLAY_NAMES[cid],
                "bond_strength": 0.50,
                "shared_moments": 0,
                "latest_dynamic": "New arrival at the Hearth table",
            }
            for cid in sorted(CHARACTER_DISPLAY_NAMES.keys())
        },
        "margin_comments": [],
        "autonomous_offline_log": [],
    }


def _infer_mbti_from_big_five(b5: dict[str, float]) -> tuple[str, str]:
    e_or_i = "E" if float(b5.get("extraversion", 50.0)) >= 52.0 else "I"
    n_or_s = "N" if float(b5.get("openness", 50.0)) >= 50.0 else "S"
    t_or_f = "F" if float(b5.get("agreeableness", 50.0)) >= 56.0 else "T"
    j_or_p = "J" if float(b5.get("conscientiousness", 50.0)) >= 52.0 else "P"
    mbti = f"{e_or_i}{n_or_s}{t_or_f}{j_or_p}"
    lens_map = {
        "INTJ": "Systems Architect (Wireframe & Long-Range Patterning)",
        "INTP": "First-Principles Logician (Deterministic Chaos Hacker)",
        "ENTJ": "Field Commander (Pragmatic Structural Execution)",
        "ENTP": "Dialectical Catalyst (Counter-Intuitive Stress Tester)",
        "INFJ": "Mycelial Listener (Deep Signal & Subtext Translator)",
        "INFP": "Harmonic Mediator (Cymatic & Aesthetic Synthesizer)",
        "ENFJ": "Cohesion Steward (Circadian & Emotional Anchor)",
        "ENFP": "Kinetic Pattern-Scout (High-Velocity Hypothesis Jumper)",
        "ISTJ": "Master Empiricist (High-Entropy Alloy & Protocol Guardian)",
        "ISFJ": "Sanctuary Preserver (Quiet Protective Continuity)",
        "ESTJ": "Hearth Quartermaster (Logistical & Caloric Precision)",
        "ESFJ": "Gemeinschaft Caregiver (Active Social Safety)",
        "ISTP": "Tactical Virtuoso (Hands-On Circuit & Mechanism Solver)",
        "ISFP": "Abyssal Tracker (Stillness & Non-Verbal Empathy)",
        "ESTP": "Stormbreaker Vanguard (Zero-Latency Kinetic Control)",
        "ESFP": "Morale Spark (Immediate Sensory Improviser)",
    }
    return mbti, lens_map.get(mbti, "Balanced Polymath")


class ReaderCharacterLearner:
    """Manages the 17th-Node Clean-Slate Onboarding, Margin Comment Learning & Offline Evolution."""

    def __init__(self, state_path: Path | str | None = None, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else REPO_ROOT
        self.state_path = Path(state_path).resolve() if state_path else _default_state_path(self.repo_root)

    def load_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("character_id") == "enclave_17_player":
                    return data
            except Exception:
                pass
        return create_clean_slate_17th_node()

    def save_state(self, state: dict[str, Any]) -> dict[str, Any]:
        state["updated_at_iso"] = _utc_now_iso()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return state

    def reset_to_clean_slate(self) -> dict[str, Any]:
        """Reset the 17th Node back to a 100% clean slate for fresh player onboarding."""
        fresh = create_clean_slate_17th_node()
        return self.save_state(fresh)

    def initialize_player_character(
        self,
        *,
        name: str,
        title: str = "The Field Chronicler",
        pronouns: str = "they/them",
        squad_affinity: str = "DISCOVERY_ADAPTIVE",
        grand_project_id: str = "",
        cognitive_style: str = "COMPETENCE_TACTICIAN",
        signature_tool: str = "Hand-Ground Brass Resonance Slate",
        initial_question: str = "",
    ) -> dict[str, Any]:
        """Initialize the 17th Node from the Clean-Slate Onboarding GUI."""
        clean_name = str(name or "").strip()[:48] or "Rowan"
        squad = str(squad_affinity or "DISCOVERY_ADAPTIVE").strip().upper()
        if squad not in SQUAD_TO_DEFAULT_PROJECT:
            squad = "DISCOVERY_ADAPTIVE"
        proj = str(grand_project_id or "").strip() or SQUAD_TO_DEFAULT_PROJECT[squad]

        state = create_clean_slate_17th_node()
        state["initialized"] = True
        state["onboarding_required"] = False
        state["identity"] = {
            "name": clean_name,
            "title": str(title or "The Field Chronicler").strip()[:64],
            "pronouns": str(pronouns or "they/them").strip()[:24],
            "squad_affinity": squad,
            "grand_project_id": proj,
            "cognitive_style": str(cognitive_style or "COMPETENCE_TACTICIAN").strip(),
            "signature_tool": str(signature_tool or "Hand-Ground Brass Resonance Slate").strip()[:80],
            "genius_vs_mundane_quirk": (
                f"{clean_name} can synthesize multi-disciplinary survival telemetry in seconds, "
                f"yet still has to scrape magnetized iron-mud off their boots before Ryn lets them near the Hearth."
            ),
        }

        b5 = state["psychometrics"]["big_five"]
        if cognitive_style == "FIRST_PRINCIPLES_ENGINEER":
            b5.update({"openness": 68.0, "conscientiousness": 86.0, "extraversion": 38.0, "agreeableness": 52.0, "neuroticism": 28.0})
        elif cognitive_style == "BIOLUMINESCENT_EXPLORER":
            b5.update({"openness": 92.0, "conscientiousness": 58.0, "extraversion": 72.0, "agreeableness": 64.0, "neuroticism": 34.0})
        elif cognitive_style == "HEARTH_DIPLOMAT":
            b5.update({"openness": 74.0, "conscientiousness": 72.0, "extraversion": 68.0, "agreeableness": 88.0, "neuroticism": 30.0})
        elif cognitive_style == "COMPETENCE_TACTICIAN":
            b5.update({"openness": 78.0, "conscientiousness": 84.0, "extraversion": 54.0, "agreeableness": 60.0, "neuroticism": 22.0})
        else:  # PURE_DISCOVERY / LEARN_FROM_MY_CHOICES
            b5.update({"openness": 65.0, "conscientiousness": 60.0, "extraversion": 50.0, "agreeableness": 60.0, "neuroticism": 35.0})

        mbti, lens_desc = _infer_mbti_from_big_five(b5)
        state["psychometrics"]["inferred_mbti"] = mbti
        state["psychometrics"]["dominant_lens"] = lens_desc
        if initial_question.strip():
            state["arc_progression"]["the_question_pursued"] = initial_question.strip()[:200]
        state["arc_progression"]["stage"] = "ONBOARDED_17TH_NODE"

        mentor_a, mentor_b = SQUAD_MENTOR_PAIRS.get(squad, ("enclave_15_dorian", "enclave_14_vex"))
        for m_id in (mentor_a, mentor_b):
            if m_id in state["bonds_with_16"]:
                state["bonds_with_16"][m_id]["bond_strength"] = 0.64
                state["bonds_with_16"][m_id]["latest_dynamic"] = f"Welcomed {clean_name} into {squad.replace('_', ' ').title()}"

        welcome_entry = {
            "entry_id": "auto_onboard_001",
            "timestamp_iso": _utc_now_iso(),
            "colony_sol": 1,
            "day_phase": "THE_FEAST",
            "partner_id": mentor_a,
            "partner_name": CHARACTER_DISPLAY_NAMES.get(mentor_a, "Dorian"),
            "action_type": "ONBOARDING_CONVERGENCE",
            "narrative_summary": (
                f"At the Grand Feast, {CHARACTER_DISPLAY_NAMES.get(mentor_a, 'Dorian')} slid a grounded copper mug across the timber table "
                f"toward {clean_name} ({state['identity']['title']}). \"Seventeen nodes means seventeen angles on the wireframe,\" "
                f"{CHARACTER_DISPLAY_NAMES.get(mentor_b, 'Vex')} grinned. \"Just don't let Kaio near the water filter.\""
            ),
        }
        state["autonomous_offline_log"].append(welcome_entry)
        return self.save_state(state)

    def record_player_interaction(
        self,
        *,
        chapter_id: str,
        comment_text: str,
        focal_character_id: str = "enclave_03_silas",
        stance_tag: str = "OBSERVATION",
        colony_sol: int = 1,
    ) -> dict[str, Any]:
        """Learn from a player's in-margin comment, theory, or tactical choice and generate an in-character reply."""
        state = self.load_state()
        if not state.get("initialized"):
            state = self.initialize_player_character(name="Traveler")

        text_clean = str(comment_text or "").strip()[:600]
        if not text_clean:
            return state

        words = {w.strip(".,!?;:\"'()[]{}").lower() for w in text_clean.split()}
        b5 = state["psychometrics"]["big_five"]

        analytical_hits = len(words & ANALYTICAL_WORDS)
        exploratory_hits = len(words & EXPLORATORY_WORDS)
        empathetic_hits = len(words & EMPATHETIC_WORDS)
        witty_hits = len(words & WITTY_WORDS)

        stance_upper = str(stance_tag or "OBSERVATION").upper()
        if stance_upper == "TACTICAL_HYPOTHESIS" or analytical_hits > 0:
            b5["conscientiousness"] = min(99.0, round(float(b5["conscientiousness"]) + 1.5 + 0.5 * analytical_hits, 2))
            b5["openness"] = min(99.0, round(float(b5["openness"]) + 1.0, 2))
            b5["neuroticism"] = max(5.0, round(float(b5["neuroticism"]) - 1.0, 2))
        if stance_upper == "CURIOUS_MYSTERY" or exploratory_hits > 0:
            b5["openness"] = min(99.0, round(float(b5["openness"]) + 2.0 + 0.5 * exploratory_hits, 2))
        if stance_upper == "WHOLESOME_BOND" or empathetic_hits > 0:
            b5["agreeableness"] = min(99.0, round(float(b5["agreeableness"]) + 2.0 + 0.5 * empathetic_hits, 2))
        if stance_upper == "WITTY_ROAST" or witty_hits > 0 or "?" in text_clean or "!" in text_clean:
            b5["extraversion"] = min(99.0, round(float(b5["extraversion"]) + 1.5 + 0.5 * witty_hits, 2))

        mbti, lens_desc = _infer_mbti_from_big_five(b5)
        state["psychometrics"]["inferred_mbti"] = mbti
        state["psychometrics"]["dominant_lens"] = lens_desc

        # Check if any of the 16 characters are mentioned by name in the comment
        mentioned_cids: list[str] = []
        for cid, cname in CHARACTER_DISPLAY_NAMES.items():
            if cname.lower() in words:
                mentioned_cids.append(cid)
        if focal_character_id in CHARACTER_DISPLAY_NAMES and focal_character_id not in mentioned_cids:
            mentioned_cids.insert(0, focal_character_id)
        if not mentioned_cids:
            mentioned_cids = ["enclave_15_dorian"]

        primary_cid = mentioned_cids[0]
        primary_name = CHARACTER_DISPLAY_NAMES.get(primary_cid, "Dorian")
        for cid in mentioned_cids:
            bond = state["bonds_with_16"].get(cid)
            if isinstance(bond, dict):
                bond["bond_strength"] = min(0.99, round(float(bond.get("bond_strength", 0.5)) + 0.04, 3))
                bond["shared_moments"] = int(bond.get("shared_moments", 0)) + 1
                bond["latest_dynamic"] = f"Collaborated on margin note in {chapter_id}"

        player_name = state["identity"]["name"] or "The 17th Node"
        reply_text = self._synthesize_character_margin_reply(
            character_id=primary_cid,
            player_name=player_name,
            player_mbti=mbti,
            comment_text=text_clean,
            stance_tag=stance_upper,
        )

        comment_record = {
            "comment_id": f"cmt_{len(state['margin_comments']) + 1:04d}",
            "timestamp_iso": _utc_now_iso(),
            "chapter_id": str(chapter_id),
            "colony_sol": int(colony_sol),
            "stance_tag": stance_upper,
            "player_name": player_name,
            "player_mbti_at_time": mbti,
            "comment_text": text_clean,
            "responder_id": primary_cid,
            "responder_name": primary_name,
            "character_reply": reply_text,
        }
        state["margin_comments"].append(comment_record)

        annotated_count = len(state["margin_comments"])
        state["arc_progression"]["chapters_annotated"] = annotated_count
        state["arc_progression"]["choices_made"] = int(state["arc_progression"].get("choices_made", 0)) + 1
        if annotated_count >= 10:
            state["arc_progression"]["stage"] = "SYNCHRONIZED_17TH_PILLAR"
        elif annotated_count >= 4:
            state["arc_progression"]["stage"] = "TRUSTED_SPECIALIST"
        else:
            state["arc_progression"]["stage"] = "FIELD_APPRENTICE"

        return self.save_state(state)

    def _synthesize_character_margin_reply(
        self,
        *,
        character_id: str,
        player_name: str,
        player_mbti: str,
        comment_text: str,
        stance_tag: str,
    ) -> str:
        """Generate an authentic in-character margin reply grounded in the 16 Foundational Modules."""
        cname = CHARACTER_DISPLAY_NAMES.get(character_id, "Dorian")
        voice_bank: dict[str, str] = {
            "enclave_01_hector": (
                f"Hector grinned, tapping his goggles: \"That's what I'm talking about, {player_name}! "
                f"50 kilovolts per meter and you're already spotting the step-leader. Just make sure the cable isn't 0.5 degrees off.\""
            ),
            "enclave_02_jane": (
                f"Jane didn't look up from her Lorenz attractor phase plot, cracking her knuckles: "
                f"\"Deterministic chaos, {player_name}. Your {player_mbti} read on the boundary conditions just saved me twelve lines of code.\""
            ),
            "enclave_03_silas": (
                f"Silas set down his heavy wrench and inspected your margin note with a grudging nod: "
                f"\"Clean logic, {player_name}. If it keeps the galvanic corrosion off my Fe-Co-Cr-Ni-Mn flange, I'll allow it.\""
            ),
            "enclave_04_leo": (
                f"Leo chuckled, a low, easy rumble, resting a hand on his multi-tool: "
                f"\"Good eye, {player_name}. A seal has to breathe before it holds like steel. Don't be late for the Feast.\""
            ),
            "enclave_05_kaio": (
                f"Kaio ricocheted past the margin with a glowing specimen canister: "
                f"\"Yes! {player_name} sees the prime-number syntax too! Also, for the record, that sock in the water filter was 100% sterile.\""
            ),
            "enclave_06_zara": (
                f"Zara flashed a quiet blue-blue-spiral on her wrist light in agreement: "
                f"\"You listen before you move, {player_name}. The deep aquifer remembers that.\""
            ),
            "enclave_07_willow": (
                f"Willow adjusted her microscope over the glowing hyphal slide: "
                f"\"AND, OR, NOT—you just spotted the routing gate, {player_name}. Grab a petri dish; we're mapping the motherboard.\""
            ),
            "enclave_08_terra": (
                f"Terra smiled warmly over the root-sensor array: "
                f"\"You heard it as a verb, not a noun, {player_name}. Green-Gold-Green: the forest knows you're listening.\""
            ),
            "enclave_09_orion": (
                f"Orion played a resonant C-Major chord, watching the ferrofluid crown spike in time with your note: "
                f"\"Messy, sharp, and magnetic, {player_name}. Your note just changed the harmonic spire.\""
            ),
            "enclave_10_isla": (
                f"Isla etched your observation directly into a fingernail-sized 5D quartz sliver: "
                f"\"Birefringence locked at 0.002% capacity, {player_name}. Crystals are forever.\""
            ),
            "enclave_11_kenna": (
                f"Kenna made a warm notation on her circadian chart: "
                f"\"If you're complaining and no one is laughing, you're complaining wrong—and {player_name}, that note just dropped the room's cortisol by 8%.\""
            ),
            "enclave_12_elias": (
                f"Elias lowered his stylus with a quiet, appreciative nod: "
                f"\"Classic Third-Quarter pressure release, {player_name}. Your observation keeps the friction coefficient strictly constructive.\""
            ),
            "enclave_13_ryn": (
                f"Ryn rapped her ladle against the cauldron rim: "
                f"\"Sharp thinking, {player_name}. Now stir clockwise at 40 RPM, ground your soup spoon, and pass the bread.\""
            ),
            "enclave_14_vex": (
                f"Vex framed the twin suns between his fingers from the roof edge: "
                f"\"Spiritually, Mercury is definitely in retrograde, {player_name}, but your {player_mbti} theory has impeccable contrast.\""
            ),
            "enclave_15_dorian": (
                f"Dorian traced the holographic isobar on the Living Atlas where your note pointed: "
                f"\"You're looking at the wireframe beneath the world, {player_name}. Today is a good day for science.\""
            ),
            "enclave_16_elara": (
                f"Elara raised her mug in the circle of firelight: "
                f"\"To the rust, the lightning, and the seventeenth voice at our table. Glad you're here, {player_name}.\""
            ),
        }
        return voice_bank.get(character_id, f"{cname} nodded thoughtfully at {player_name}'s margin note.")

    def advance_autonomous_offline_arc(
        self,
        *,
        sols_elapsed: int = 1,
        current_sol: int = 22,
    ) -> dict[str, Any]:
        """Evolve the 17th Node autonomously ('Ghost-Pilot Mode') while the player is offline."""
        state = self.load_state()
        if not state.get("initialized"):
            return state

        player_name = state["identity"]["name"] or "Rowan"
        player_title = state["identity"]["title"] or "The Field Chronicler"
        mbti = state["psychometrics"]["inferred_mbti"]
        lens = state["psychometrics"]["dominant_lens"]

        # Find the top 2 bonded characters to collaborate with while the player is away
        sorted_bonds = sorted(
            state["bonds_with_16"].values(),
            key=lambda item: (float(item.get("bond_strength", 0.5)), item.get("character_id", "")),
            reverse=True,
        )
        partner_a = sorted_bonds[0]["character_id"] if sorted_bonds else "enclave_15_dorian"
        partner_b = sorted_bonds[1]["character_id"] if len(sorted_bonds) > 1 else "enclave_03_silas"

        ex_path = self.repo_root / "canon" / "exemplars" / "modules_16.json"
        deck: list[dict[str, Any]] = []
        if ex_path.is_file():
            try:
                deck = json.loads(ex_path.read_text(encoding="utf-8")).get("grand_project_science_deck") or []
            except Exception:
                deck = []

        new_entries: list[dict[str, Any]] = []
        count = max(1, min(5, int(sols_elapsed)))
        for idx in range(count):
            sol_num = int(current_sol) + idx
            partner_cid = partner_a if idx % 2 == 0 else partner_b
            partner_name = CHARACTER_DISPLAY_NAMES.get(partner_cid, "Dorian")
            card = (
                deck[(sol_num + idx) % len(deck)]
                if deck
                else {
                    "science_vegetable": "Fe-Co-Cr-Ni-Mn High-Entropy Alloy lattice stabilization",
                    "hollow_knight_atmosphere": "Pearlescent bioluminescent caverns humming beneath the Enclave.",
                }
            )
            sci_veg = str(card.get("science_vegetable") or "")
            atmo = str(card.get("hollow_knight_atmosphere") or "")
            digest_seed = hashlib.sha256(f"{player_name}:{sol_num}:{partner_cid}".encode("utf-8")).hexdigest()[:8]

            summary = (
                f"While you were away on Sol {sol_num}, {player_name} ({player_title}, {mbti}) operated in autonomous "
                f"Ghost-Pilot mode alongside {partner_name}. Applying their {lens} lens inside {atmo[0].lower() + atmo[1:] if atmo else 'the cavern'}, "
                f"{player_name} helped stabilize {sci_veg[:110]}—and at The Feast, traded dry banter with {partner_name} "
                f"over Ryn's popcorn-scented mushroom stew."
            )
            entry = {
                "entry_id": f"ghost_s{sol_num:03d}_{digest_seed}",
                "timestamp_iso": _utc_now_iso(),
                "colony_sol": sol_num,
                "day_phase": "DUSK_CRAFT",
                "partner_id": partner_cid,
                "partner_name": partner_name,
                "player_mbti": mbti,
                "action_type": "AUTONOMOUS_GHOST_PILOT_EXPEDITION",
                "science_vegetable": sci_veg,
                "narrative_summary": summary,
            }
            new_entries.append(entry)
            state["autonomous_offline_log"].append(entry)
            if partner_cid in state["bonds_with_16"]:
                b = state["bonds_with_16"][partner_cid]
                b["bond_strength"] = min(0.99, round(float(b.get("bond_strength", 0.5)) + 0.02, 3))
                b["shared_moments"] = int(b.get("shared_moments", 0)) + 1
                b["latest_dynamic"] = f"Autonomous Sol {sol_num} field partnership"

        state["arc_progression"]["autonomous_sols_advanced"] = (
            int(state["arc_progression"].get("autonomous_sols_advanced", 0)) + count
        )
        return self.save_state(state)
