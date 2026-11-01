"""Cross-Medium Narrative Architecture & Computational Prose Calibration Engine.

Implements the unified biomechanical, dramatic, epistemic, oral, topological, and
computational prose calibration pipeline for 'The Enclave of the 16':

1. Biomechanical Narrative Propulsion:
   - Willingham's Four Cs (Causality, Conflict, Complications, Character)
   - Stanton's '2 + 2' Unifying Theory (anchored to Character Spine; withholds '= 4')
   - Parker & Stone's 'But and Therefore' Rule (bans 'and then' chronological logs)
   - Dwight Swain's Scene (Goal -> Conflict -> Disaster [FLAT_NO | YES_BUT |
     NO_AND_FURTHERMORE | INVERTED_DISASTER]) <-> Sequel (Reaction -> Dilemma
     [Coyne's Best Bad Choice / Irreconcilable Goods] -> Decision) & Micro MRUs.
2. Dramatic Compression & Eradication of Info-Dumping:
   - David Mamet's 3-Question Litmus Gate (Who wants what? What happens if not? Why now?)
   - Three Structural Danger Signals (Outline Logline 'discuss' test, Third-Party Triad
     failure, and 'As You Know, Bob' dialogue) + The Silent Movie Constraint.
3. Temporal Information Asymmetry:
   - Hitchcock's 'Bomb Under the Table' Suspense vs. Mystery ledger
   - Ronald Knox's 10 Commandments of Fair Play (Commandment VIII Camouflaged Flourishing)
   - Agatha Christie's 5-Step Backward Revision Foreshadowing Tracker & 5 Camouflage Tactics.
4. Orality, Vulnerability & Pedagogical Pacing:
   - Ira Glass (Anecdote with Bait + Moment of Reflection)
   - Jad Abumrad (47% Gut Churn Index + No Plexi-Glass raw specialist doubt)
   - Dan Carlin (Multi-Perspective Source Interrogation + Visceral Extremes).
5. Emergent Interactive Topology:
   - Justin Alexander's Situation Toolbox (Faction Power Matrix + Chandler's Door-Kick)
   - Node-Based Design with the Inverted Three-Clue Rule (in-degree >= 3)
   - Brennan Lee Mulligan's Magnetic Tailoring & Hard Scene Framing.
6. Prose Mechanics & 3-Pass De-AI Calibration (StoryScope / Sepia / Hermes / Stop-Slop):
   - Chuck Palahniuk's Thought-Verb Unpacking (submerging abstract mental states into action)
   - Ursula K. Le Guin's Acoustic Rhythm & Sentence-Length Spread (sigma >= 5.0 words)
   - Three-Pass De-AI Protocol (Pass 1 Architecture, Pass 2 Discourse De-Templating,
     Pass 3 Surface Lexical Sanitization + Pattern 30 & Pattern 31 eradication)
   - Law of Moderate Human Distribution (3-5 architectural moves per scene)
   - Quantitative 5-Dimension Stop-Slop Scorer (Directness, Rhythm, Trust,
     Authenticity, Density >= 35/50).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any


# ---------------------------------------------------------------------------
# 1. Biomechanical Narrative Propulsion (Swain Scene/Sequel + But/Therefore)
# ---------------------------------------------------------------------------

CANONICAL_DISASTER_TYPES: tuple[str, ...] = (
    "FLAT_NO",
    "YES_BUT",
    "NO_AND_FURTHERMORE",
    "INVERTED_DISASTER",  # Reserved exclusively for Act III Defining Moment
)

CANONICAL_CAUSAL_CONNECTORS: tuple[str, ...] = ("BUT", "THEREFORE")

CHARACTER_SPINES: dict[str, dict[str, str]] = {
    "enclave_01_hector": {
        "spine": "Protect the perimeter through absolute kinetic readiness before the wild takes a single life.",
        "lie_believed": "A shield that bends for even a second has already failed the family.",
        "truth_to_learn": "Shared vulnerability across the squad is stronger than solitary armor.",
    },
    "enclave_02_jane": {
        "spine": "Extract clean signal from atmospheric noise so no expedition walks blind.",
        "lie_believed": "Emotion in a telemetry channel is just another form of packet loss.",
        "truth_to_learn": "The human voice behind the carrier wave is the signal worth saving.",
    },
    "enclave_03_silas": {
        "spine": "Arrest thermodynamic decay through precision metallurgy and unyielding craft.",
        "lie_believed": "If a joint or alloy cannot endure three centuries of shear, the builder is a fraud.",
        "truth_to_learn": "Living systems endure by flexing with entropy rather than fighting it alone.",
    },
    "enclave_04_leo": {
        "spine": "Turn impossible mechanical failure into kinetic momentum with whatever scrap is in reach.",
        "lie_believed": "If he stops moving or joking for ten seconds, the weight of the crater will crush morale.",
        "truth_to_learn": "Stillness and asking for a second wrench are marks of mastery, not weakness.",
    },
    "enclave_05_kaio": {
        "spine": "Decode the planetary magnetosphere before the twin-sun cycle strips the grid.",
        "lie_believed": "Every anomaly can be reduced to a clean differential equation in isolation.",
        "truth_to_learn": "Field intuition and human trust bridge the gaps where instruments saturate.",
    },
    "enclave_06_zara": {
        "spine": "Map the subterranean mycelial intelligence without corrupting its native equilibrium.",
        "lie_believed": "Empirical detachment requires keeping her own pulse out of the specimen log.",
        "truth_to_learn": "The observer is already braided into the ecology she studies.",
    },
    "enclave_07_willow": {
        "spine": "Weave bioluminescent flora and acoustic harmony into a livable sanctuary.",
        "lie_believed": "Conflict between specialists means her garden failed to soothe the colony.",
        "truth_to_learn": "Creative friction is the compost from which real synthesis grows.",
    },
    "enclave_08_terra": {
        "spine": "Cultivate resilient soil and root-matrices capable of feeding the crater for generations.",
        "lie_believed": "If she does not shoulder the physical harvest herself, the terraces will starve.",
        "truth_to_learn": "Teaching the apprentice to tend the terrace multiplies the harvest.",
    },
    "enclave_09_orion": {
        "spine": "Navigate the deep subterranean and celestial coordinates where standard compasses spin.",
        "lie_believed": "A scout who hesitates at the threshold loses the trail for everyone behind him.",
        "truth_to_learn": "True pathfinding means anchoring the return line before leaping into the dark.",
    },
    "enclave_10_isla": {
        "spine": "Chart every subterranean fault line and cavern vault with millimeter fidelity.",
        "lie_believed": "An unmapped trench is a personal indictment of her vigilance.",
        "truth_to_learn": "Some horizons only open when you step off the surveyed datum with a partner.",
    },
    "enclave_11_kenna": {
        "spine": "Hold the rigging and high-altitude lifelines taut when the katabatic gales hit.",
        "lie_believed": "Dependence on ground control slows down the rescue.",
        "truth_to_learn": "An anchor only holds when both ends of the line trust the tension.",
    },
    "enclave_12_elias": {
        "spine": "Archive the linguistic and epistemic memory of the sixteen so nothing true is lost.",
        "lie_believed": "Recording history from the margin is safer than shaping it in the mud.",
        "truth_to_learn": "The chronicler must put boots on the basalt to earn the truth of the page.",
    },
    "enclave_13_ryn": {
        "spine": "Convert scarce alien biochemistry into warm, communal nourishment at the nightly Hearth.",
        "lie_believed": "If the stew cools or the table fractures, the sixteen cease to be a family.",
        "truth_to_learn": "The Hearth survives even when the pot boils over and the truth gets messy.",
    },
    "enclave_14_vex": {
        "spine": "Stress-test every sanctimonious rule and lock through mischievous shadow-economy ingenuity.",
        "lie_believed": "Sincere attachment is just a vulnerability waiting to be audited.",
        "truth_to_learn": "Loyalty chosen freely by a rogue is the most unbreakable contract in the Enclave.",
    },
    "enclave_15_dorian": {
        "spine": "Design load-bearing subterranean architecture worthy of outlasting the stars.",
        "lie_believed": "Order and symmetry must purge every chaotic improvisation—especially Vex's.",
        "truth_to_learn": "Vex's asymmetric contraband splices are the exact expansion joints his vaults need.",
    },
    "enclave_16_elara": {
        "spine": "Synthesize xenobotanical genetics and human resilience into a living bridge with Kepler-452b.",
        "lie_believed": "She must carry the biochemical burden of adaptation before testing it on anyone else.",
        "truth_to_learn": "Ryn's grounded culinary wisdom completes the synthesis her lab glass cannot reach alone.",
    },
}


@dataclass
class SceneBeat:
    """Proactive external action phase (Swain Scene)."""

    scene_id: str
    pov_character_id: str
    goal: str
    conflict: str
    disaster_type: str
    disaster_outcome: str
    stanton_clue_a: str
    stanton_clue_b: str
    withheld_inference_4: str
    act_number: int = 1


@dataclass
class SequelBeat:
    """Reactive internal processing phase (Swain Sequel)."""

    sequel_id: str
    pov_character_id: str
    visceral_reaction: str
    dilemma_option_a_cost: str
    dilemma_option_b_cost: str
    decision_therefore_goal: str


class SceneSequelPropulsionEngine:
    """Biomechanical state machine enforcing Parker & Stone But/Therefore and Swain Scene/Sequel."""

    @staticmethod
    def validate_scene_sequel_pair(
        scene: SceneBeat,
        sequel: SequelBeat,
        connector_history: list[str] | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []

        if not scene.goal.strip():
            errors.append("Scene missing concrete immediate Goal.")
        if not scene.conflict.strip():
            errors.append("Scene missing active Conflict.")
        if scene.disaster_type not in CANONICAL_DISASTER_TYPES:
            errors.append(f"Invalid disaster_type '{scene.disaster_type}'. Must be one of {CANONICAL_DISASTER_TYPES}.")
        if scene.disaster_type == "INVERTED_DISASTER" and scene.act_number < 3:
            errors.append("INVERTED_DISASTER is reserved exclusively for Act III Defining Moments.")
        if not scene.stanton_clue_a.strip() or not scene.stanton_clue_b.strip():
            errors.append("Stanton '2 + 2' violation: both constituent clues (2 + 2) must be supplied.")

        # Ensure the withheld synthesis ('= 4') is not explicitly blurted out verbatim in the clues
        if (
            scene.withheld_inference_4.strip()
            and len(scene.withheld_inference_4.strip()) > 12
            and scene.withheld_inference_4.strip().lower()
            in (scene.stanton_clue_a + " " + scene.stanton_clue_b).lower()
        ):
            errors.append("Stanton '2 + 2' violation: explicit '= 4' synthesis was stated inside the clues.")

        if not sequel.visceral_reaction.strip():
            errors.append("Sequel missing visceral Reaction phase.")
        if not sequel.dilemma_option_a_cost.strip() or not sequel.dilemma_option_b_cost.strip():
            errors.append("Sequel Dilemma must pit two costly options against each other (Coyne's Best Bad Choice).")
        if not sequel.decision_therefore_goal.strip():
            errors.append("Sequel Decision must formulate the causal THEREFORE goal for the next Scene.")

        history = list(connector_history or ["BUT", "THEREFORE"])
        for conn in history:
            if conn not in CANONICAL_CAUSAL_CONNECTORS:
                errors.append(f"Forbidden connector '{conn}': 'AND_THEN' chronological logs are banned.")
        # Check for >=3 consecutive THEREFORE without an intervening BUT
        consecutive_therefore = 0
        for conn in history:
            if conn == "THEREFORE":
                consecutive_therefore += 1
                if consecutive_therefore >= 3:
                    warnings.append(
                        "Chain of >=3 consecutive THEREFORE transitions without a BUT loses oppositional friction."
                    )
            else:
                consecutive_therefore = 0

        spine_info = CHARACTER_SPINES.get(scene.pov_character_id, CHARACTER_SPINES["enclave_03_silas"])
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "macro_bridge_scene_to_sequel": "BUT",
            "macro_bridge_sequel_to_next_scene": "THEREFORE",
            "character_spine": spine_info,
        }

    @staticmethod
    def validate_mru_paragraph(
        stimulus: str,
        visceral_reflex: str,
        physical_action: str,
        speech_or_thought: str = "",
    ) -> dict[str, Any]:
        """Validate a micro-level Motivation-Reaction Unit (MRU) for strict chronological causality."""
        errors: list[str] = []
        if not stimulus.strip():
            errors.append("MRU missing external sensory Motivation (stimulus).")
        if not visceral_reflex.strip() and not physical_action.strip():
            errors.append("MRU missing internal visceral reflex or physical action response.")
        # Stimulus must not contain the character's own internal thought before the external event
        if re.search(r"\b(he thought|she thought|he realized|she realized)\b", stimulus, re.IGNORECASE):
            errors.append("MRU inversion: internal thought placed inside external Motivation stimulus.")
        composed = " ".join(
            part.strip()
            for part in (stimulus, visceral_reflex, physical_action, speech_or_thought)
            if part.strip()
        )
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "composed_mru": composed,
        }


# ---------------------------------------------------------------------------
# 2. Dramatic Compression & Eradication of Info-Dumping (David Mamet Gate)
# ---------------------------------------------------------------------------

OUTLINE_LOGLINE_FAILURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(discuss|discusses|discussing|talk about|talks about|catch up on|exchanges information)\b", re.I),
)

AS_YOU_KNOW_BOB_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bas you both know\b", re.I),
    re.compile(r"\bas you know\b", re.I),
    re.compile(r"\byou know as well as I do that since\b", re.I),
    re.compile(r"\bneed I remind you that for the past\b", re.I),
)


class MametDramaticCompressionGate:
    """Enforces David Mamet's 3-Question Litmus Gate, Danger Signal Detection, and Silent Movie Constraint."""

    @staticmethod
    def evaluate_scene_unit(
        *,
        active_characters: list[str],
        who_wants_what: str,
        what_happens_if_denied: str,
        why_now: str,
        scene_logline: str,
        physical_actions_observed: list[str],
        dialogue_lines: list[str] | None = None,
        third_party_subject_id: str | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        danger_signals: list[str] = []

        if len(who_wants_what.strip()) < 10:
            errors.append("Mamet Q1 Failure: 'Who wants what?' is missing or vague.")
        if len(what_happens_if_denied.strip()) < 10:
            errors.append("Mamet Q2 Failure: 'What happens if they don't get it?' lacks concrete stakes.")
        if len(why_now.strip()) < 8:
            errors.append("Mamet Q3 Failure: 'Why now?' lacks an immediate ticking urgency trigger.")

        for pat in OUTLINE_LOGLINE_FAILURE_PATTERNS:
            if pat.search(scene_logline):
                danger_signals.append(
                    "Danger Signal 1 (Outline Logline Test): Scene summary describes characters 'discussing' "
                    "rather than pursuing an active transactional objective."
                )
                break

        if third_party_subject_id and third_party_subject_id not in active_characters:
            danger_signals.append(
                f"Danger Signal 2 (Third-Party Triad Failure): {active_characters} are talking about absent "
                f"party '{third_party_subject_id}' instead of contending directly with each other."
            )

        for dline in dialogue_lines or []:
            for pat in AS_YOU_KNOW_BOB_PATTERNS:
                if pat.search(dline):
                    danger_signals.append(
                        f"Danger Signal 3 ('As You Know, Bob' Exposition): Found shared-fact info-dump in '{dline[:60]}'."
                    )
                    break

        silent_movie_ok = len(physical_actions_observed) >= 2 and all(
            len(act.strip()) >= 8 for act in physical_actions_observed[:2]
        )
        if not silent_movie_ok:
            errors.append(
                "Silent Movie Constraint Failure: Scene must demonstrate specialist competence through >=2 "
                "observable physical actions with tools/environment without relying on dialogue."
            )

        return {
            "passed": len(errors) == 0 and len(danger_signals) == 0,
            "litmus_gate_passed": len(errors) == 0,
            "silent_movie_passed": silent_movie_ok,
            "errors": errors,
            "danger_signals": danger_signals,
        }


# ---------------------------------------------------------------------------
# 3. Temporal Information Asymmetry (Hitchcock Suspense & Knox/Christie)
# ---------------------------------------------------------------------------

CANONICAL_CAMOUFLAGE_TACTICS: tuple[str, ...] = (
    "BURY_IN_TEXTURE",
    "PAIR_WITH_EMOTION",
    "DISGUISE_AS_CHARACTER_BUSINESS",
    "PLACE_ADJACENT_TO_RED_HERRING",
    "DUAL_MEANING",
)


@dataclass
class PlantedClueNode:
    """Tracks a fair-play clue under Ronald Knox Commandment VIII & Christie Backward Revision."""

    clue_id: str
    revelation_id: str
    sensory_object: str
    anchor_scene_id: str
    camouflage_tactic: str
    immediate_mundane_reading: str
    retroactive_reframed_meaning: str
    is_red_herring: bool = False
    red_herring_secondary_purpose: str = ""


class TemporalInformationAsymmetryEngine:
    """Manages Hitchcock Bomb-Under-Table Suspense and Knox/Christie Fair-Play Foreshadowing."""

    @staticmethod
    def build_hitchcock_bomb_ledger(
        *,
        threat_id: str,
        physical_mechanism: str,
        countdown_ticks_remaining: int,
        mundane_foreground_activity: str,
        audience_informed: bool = True,
        characters_informed: bool = False,
    ) -> dict[str, Any]:
        mode = "HITCHCOCK_SUSPENSE" if (audience_informed and not characters_informed) else "CURIOSITY_MYSTERY"
        return {
            "threat_id": threat_id,
            "mode": mode,
            "physical_mechanism": physical_mechanism,
            "countdown_ticks_remaining": max(1, int(countdown_ticks_remaining)),
            "mundane_foreground_activity": mundane_foreground_activity,
            "audience_informed": audience_informed,
            "characters_informed": characters_informed,
            "dramatic_irony_active": bool(audience_informed and not characters_informed),
        }

    @staticmethod
    def verify_knox_christie_fair_play(clues: list[PlantedClueNode]) -> dict[str, Any]:
        errors: list[str] = []
        for c in clues:
            if c.camouflage_tactic not in CANONICAL_CAMOUFLAGE_TACTICS:
                errors.append(
                    f"Clue '{c.clue_id}' uses invalid camouflage tactic '{c.camouflage_tactic}'."
                )
            if not c.immediate_mundane_reading.strip() or not c.retroactive_reframed_meaning.strip():
                errors.append(
                    f"Clue '{c.clue_id}' must define both an immediate mundane reading and a retroactive reframed truth."
                )
            if c.is_red_herring and not c.red_herring_secondary_purpose.strip():
                errors.append(
                    f"Red herring '{c.clue_id}' violates fair-play economy: must serve a secondary character, "
                    f"comedic, or worldbuilding purpose."
                )
        return {
            "valid": len(errors) == 0,
            "knox_commandment_viii_camouflaged_flourishing": len(errors) == 0,
            "clue_count": len(clues),
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# 4. Orality, Vulnerability & Pedagogical Pacing (Glass / Abumrad / Carlin)
# ---------------------------------------------------------------------------

class OralityAndAudioCalibrationEngine:
    """Calibrates audio narration scripts for KineticEngine acoustic blocks."""

    @staticmethod
    def compose_calibrated_acoustic_script(
        *,
        chapter_id: str,
        lead_specialist_name: str,
        co_specialist_name: str,
        anecdote_with_bait: str,
        abumrad_gut_churn_doubt: str,
        carlin_conflicting_source_a: str,
        carlin_conflicting_source_b: str,
        visceral_extreme_prompt: str,
        moment_of_reflection: str,
        gut_churn_ratio: float = 0.47,
    ) -> dict[str, Any]:
        clamped_churn = round(max(0.25, min(0.70, float(gut_churn_ratio))), 2)
        script_blocks = [
            {
                "beat_type": "IRA_GLASS_ANECDOTE_WITH_BAIT",
                "speaker": lead_specialist_name,
                "text": anecdote_with_bait.strip(),
            },
            {
                "beat_type": "JAD_ABUMRAD_NO_PLEXIGLASS_DOUBT",
                "speaker": f"{lead_specialist_name} & {co_specialist_name}",
                "gut_churn_index": clamped_churn,
                "text": abumrad_gut_churn_doubt.strip(),
            },
            {
                "beat_type": "DAN_CARLIN_SOURCE_INTERROGATION",
                "speaker": "Archive Chronicler (Elias)",
                "source_a": carlin_conflicting_source_a.strip(),
                "source_b": carlin_conflicting_source_b.strip(),
                "visceral_extreme": visceral_extreme_prompt.strip(),
                "text": (
                    f"Compare the two primary logs. First: {carlin_conflicting_source_a.strip()} "
                    f"Yet twenty meters down-trench: {carlin_conflicting_source_b.strip()} "
                    f"{visceral_extreme_prompt.strip()}"
                ),
            },
            {
                "beat_type": "IRA_GLASS_MOMENT_OF_REFLECTION",
                "speaker": lead_specialist_name,
                "text": moment_of_reflection.strip(),
            },
        ]
        return {
            "chapter_id": chapter_id,
            "oral_architecture": "GLASS_ABUMRAD_CARLIN_TRIAD",
            "gut_churn_index": clamped_churn,
            "tv_broadcaster_voice_purged": True,
            "blocks": script_blocks,
        }


# ---------------------------------------------------------------------------
# 5. Emergent Interactive Topology (Alexander / Chandler / Mulligan)
# ---------------------------------------------------------------------------

@dataclass
class FactionPowerMatrixEntry:
    """Alexander Situation Toolbox Faction Definition."""

    faction_id: str
    identity: str
    acute_desire: str
    method: str
    two_adjective_personality: tuple[str, str]
    resource_or_power: str


@dataclass
class DiscoveryNode:
    """Node-Based Design discovery target enforcing the Inverted Three-Clue Rule."""

    node_id: str
    title: str
    incoming_clue_vectors: list[dict[str, str]] = field(default_factory=list)


class EmergentTopologyEngine:
    """Validates Justin Alexander's Inverted Three-Clue Rule, Chandler's Door-Kick, and Mulligan Framing."""

    @staticmethod
    def validate_inverted_three_clue_rule(nodes: list[DiscoveryNode]) -> dict[str, Any]:
        errors: list[str] = []
        node_degrees: dict[str, int] = {}
        for node in nodes:
            in_deg = len(node.incoming_clue_vectors)
            node_degrees[node.node_id] = in_deg
            if in_deg < 3:
                errors.append(
                    f"DiscoveryNode '{node.node_id}' has in-degree {in_deg} (< 3); violates Alexander's "
                    f"Inverted Three-Clue Rule."
                )
        return {
            "valid": len(errors) == 0,
            "node_in_degrees": node_degrees,
            "errors": errors,
        }

    @staticmethod
    def build_situation_toolbox(
        *,
        situation_id: str,
        initial_state: str,
        factions: list[FactionPowerMatrixEntry],
        environmental_rules: list[str],
        chandler_door_kick_trigger: str,
        mulligan_pre_roll_dc: int,
        focal_character_id: str,
    ) -> dict[str, Any]:
        spine = CHARACTER_SPINES.get(focal_character_id, CHARACTER_SPINES["enclave_03_silas"])
        return {
            "situation_id": situation_id,
            "prep_philosophy": "PREP_SITUATIONS_NOT_PLOTS",
            "initial_state": initial_state,
            "faction_power_matrix": [
                {
                    "faction_id": f.faction_id,
                    "identity": f.identity,
                    "acute_desire": f.acute_desire,
                    "method": f.method,
                    "two_adjective_personality": list(f.two_adjective_personality),
                    "resource_or_power": f.resource_or_power,
                }
                for f in factions
            ],
            "environmental_rules": list(environmental_rules),
            "chandler_door_kick_trigger": chandler_door_kick_trigger,
            "mulligan_hard_framing": {
                "enter_in_media_res": True,
                "anti_politeness_cut_on_circular_planning": True,
                "explicit_pre_roll_dc": max(8, min(25, int(mulligan_pre_roll_dc))),
                "magnetic_spine_hook": spine["spine"],
            },
        }


# ---------------------------------------------------------------------------
# 6. Prose Mechanics & 3-Pass De-AI Calibration (Palahniuk / Le Guin / Stop-Slop)
# ---------------------------------------------------------------------------

# Prohibited abstract AI-isms & stock clichés from the Treatise
PROHIBITED_AI_ISMS_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Pass 1: Moralizing tail / theme-explaining suffixes (Hemingway Iceberg omission)
    (
        re.compile(
            r"\s*(?:It was a (?:stark |quiet )?reminder that|In the end,?\s+they realized that|"
            r"A testament to their resilience[^.]*\.)\s*$",
            re.IGNORECASE,
        ),
        "",
    ),
    # Pass 2: Rhetorical Question -> Immediate Self-Answer discourse template
    (
        re.compile(r"\b(?:Why\?\s*Because|Did it matter\?\s*Not when|Was it dangerous\?\s*Certainly,?\s*but)\s+", re.I),
        "",
    ),
    # Pass 3: Pattern 30 (explaining a metaphor immediately after deploying it)
    (
        re.compile(r",\s*a\s+(?:stark\s+|vivid\s+)?(?:symbol|metaphor|testament|reminder)\s+of\s+[^,.]+(?=[,.])", re.I),
        "",
    ),
    # Pass 3: Pattern 31 (staccato subjectless mic-drop poster fragments at paragraph end)
    (
        re.compile(r"\s+(?:Pure silence\.\s*Nothing more\.|Full stop\.|No turning back now\.)\s*$", re.I),
        "",
    ),
    # Pass 3: Lexical AI-isms & stock clichés
    (re.compile(r"\bdelve(?:d|s|ing)?\s+into\b", re.I), "probed"),
    (re.compile(r"\ba\s+rich\s+tapestry\s+of\b", re.I), "a braided lattice of"),
    (re.compile(r"\btapestry\b", re.I), "lattice"),
    (re.compile(r"\btestament\s+to\b", re.I), "proof of"),
    (re.compile(r"\bin\s+the\s+realm\s+of\b", re.I), "within"),
    (re.compile(r"\bcacophony\b", re.I), "clatter"),
    (re.compile(r"\bunwavering\b", re.I), "steady"),
    (re.compile(r"\bparamount\b", re.I), "critical"),
    (re.compile(r"\bpivotal\b", re.I), "load-bearing"),
    (re.compile(r"\bunderscore(?:d|s)?\b", re.I), "marked"),
    (re.compile(r"\bshowcasing\b", re.I), "exposing"),
    (re.compile(r"\bshivers\s+down\s+(?:his|her|their)\s+spine\b", re.I), "a cold prickle across the neck"),
    (re.compile(r"\ba\s+lump\s+in\s+(?:his|her|their)\s+throat\b", re.I), "a dry catch in the glottis"),
    (re.compile(r"\bcould(?:n't|\s+not)\s+help\s+but\s+feel\b", re.I), "registered"),
    (re.compile(r"\bcarried\s+the\s+weight\s+of\b", re.I), "bore the load of"),
    (re.compile(r"\bbarely\s+above\s+a\s+whisper\b", re.I), "under the vent hum"),
    (re.compile(r"\bever\s+so\s+slightly\b", re.I), "by two millimeters"),
    (
        re.compile(r"\b(inexorably|languidly|fervently|coyly|knowingly|dreamily)\b", re.I),
        "",
    ),
)

# Palahniuk Thought-Verbs to flag or unpack into physical evidence
PALAHNIUK_THOUGHT_VERB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b([A-Z][a-z]+)\s+knew\s+that\s+the\s+pressure\s+was\s+rising\b"),
        r"\1 watched the Bourdon tube needleclimb past redline",
    ),
    (
        re.compile(r"\b([A-Z][a-z]+)\s+realized\s+that\b", re.I),
        r"\1 caught the shift in the gauge as",
    ),
    (
        re.compile(r"\b([A-Z][a-z]+)\s+felt\s+nervous\b", re.I),
        r"\1 wiped a slick palm across the canvas knee-pad",
    ),
)

ABSTRACT_THOUGHT_VERB_DETECTOR = re.compile(
    r"\b(realized|believed|imagined|desired|remembered|wondered)\b",
    re.IGNORECASE,
)

PROHIBITED_SLOP_DETECTOR = re.compile(
    r"\b(tapestry|testament|delve|delved|cacophony|unwavering|paramount|showcasing|"
    r"inexorably|languidly|fervently|coyly|dreamily)\b|"
    r"(shivers down (?:his|her|their) spine|lump in (?:his|her|their) throat|"
    r"couldn't help but feel|barely above a whisper|ever so slightly|Why\?\s*Because)",
    re.IGNORECASE,
)


def compute_sentence_length_stats(text: str) -> dict[str, float]:
    """Compute Ursula K. Le Guin acoustic sentence-length spread (mean, std_dev, min, max)."""
    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", str(text or "").strip())
        if s.strip()
    ]
    if not raw_sentences:
        return {"count": 0.0, "mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
    lengths = [len(re.findall(r"[A-Za-z0-9'-]+", s)) for s in raw_sentences]
    lengths = [L for L in lengths if L > 0]
    if not lengths:
        return {"count": 0.0, "mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
    mean_len = sum(lengths) / len(lengths)
    if len(lengths) > 1:
        variance = sum((L - mean_len) ** 2 for L in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0
    return {
        "count": float(len(lengths)),
        "mean": round(mean_len, 2),
        "std_dev": round(std_dev, 2),
        "min": float(min(lengths)),
        "max": float(max(lengths)),
    }


def run_three_pass_de_ai_calibration(raw_text: str) -> dict[str, Any]:
    """Execute the 3-Pass Sepia / Hermes / StoryScope / Stop-Slop prose calibration pipeline."""
    text = str(raw_text or "").strip()
    if not text:
        return {
            "calibrated_text": "",
            "moves_applied": [],
            "sentence_stats": compute_sentence_length_stats(""),
            "stop_slop_audit": score_stop_slop_5d(""),
        }

    moves_applied: list[str] = []

    # Pass 1 & 2 & 3 regex sanitization
    for pat, repl in PROHIBITED_AI_ISMS_REPLACEMENTS:
        if pat.search(text):
            text = pat.sub(repl, text)
            moves_applied.append(f"purged_pattern:{pat.pattern[:32]}")

    # Palahniuk Thought-Verb Unpacking
    for pat, repl in PALAHNIUK_THOUGHT_VERB_PATTERNS:
        if pat.search(text):
            text = pat.sub(repl, text)
            moves_applied.append("unpacked_palahniuk_thought_verb")

    # Normalize whitespace left by adverb/suffix removal
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text).strip()

    # Le Guin Sentence-Length Spread check: if >=3 sentences exist but std_dev < 4.5
    # (monotonous medium-length AI rhythm), append a short percussive 3-word tactile beat
    # only if within the Law of Moderate Human Distribution (<= 5 moves).
    stats = compute_sentence_length_stats(text)
    if stats["count"] >= 2 and stats["std_dev"] < 4.5 and len(moves_applied) < 5:
        if not text.endswith((".", "!", "?", '"')):
            text += "."
        text += " The gauge held."
        moves_applied.append("le_guin_percussive_short_beat_contrast")
        stats = compute_sentence_length_stats(text)

    audit = score_stop_slop_5d(text)
    return {
        "calibrated_text": text,
        "moves_applied": moves_applied[:5],
        "moderate_human_distribution_respected": len(moves_applied) <= 5,
        "sentence_stats": stats,
        "stop_slop_audit": audit,
    }


def score_stop_slop_5d(text: str) -> dict[str, Any]:
    """Score prose 1..10 across Directness, Rhythm, Trust, Authenticity, and Density (Pass >= 35/50)."""
    clean = str(text or "").strip()
    if not clean:
        return {
            "directness": 1,
            "rhythm": 1,
            "trust": 1,
            "authenticity": 1,
            "density": 1,
            "total_score": 5,
            "passed": False,
            "threshold": 35,
        }

    slop_hits = len(PROHIBITED_SLOP_DETECTOR.findall(clean))
    thought_verb_hits = len(ABSTRACT_THOUGHT_VERB_DETECTOR.findall(clean))
    stats = compute_sentence_length_stats(clean)
    words = re.findall(r"[A-Za-z0-9'-]+", clean)
    word_count = max(1, len(words))

    # 1. Directness (penalize hedging, passive throat-clearing, moralizing tails)
    hedges = len(re.findall(r"\b(somewhat|arguably|it is worth noting|needless to say|sort of)\b", clean, re.I))
    directness = max(1, min(10, 9 - hedges * 2 - (1 if slop_hits > 0 else 0)))

    # 2. Rhythm (Le Guin sentence-length variance)
    if stats["count"] <= 1:
        rhythm = 7
    elif stats["std_dev"] >= 5.5:
        rhythm = 9
    elif stats["std_dev"] >= 4.0:
        rhythm = 8
    elif stats["std_dev"] >= 2.5:
        rhythm = 6
    else:
        rhythm = 4

    # 3. Trust (Reader inference respected: zero 'Why? Because', zero Pattern 30 metaphor explanation)
    trust_penalties = len(
        re.findall(r"(Why\?\s*Because|which symboli[sz]ed|a reminder that|teaching them that)", clean, re.I)
    )
    trust = max(1, min(10, 9 - trust_penalties * 3))

    # 4. Authenticity (Zero AI-isms + Palahniuk concrete physical verbs)
    authenticity = max(1, min(10, 9 - slop_hits * 3 - thought_verb_hits))

    # 5. Density (Concrete specificity: numbers, technical/tactile tokens, long words ratio)
    specific_tokens = [w for w in words if len(w) >= 6 or any(ch.isdigit() for ch in w)]
    specificity_ratio = len(specific_tokens) / float(word_count)
    density = max(1, min(10, int(round(5 + min(4.5, specificity_ratio * 14.0))) - (1 if slop_hits > 1 else 0)))

    total = directness + rhythm + trust + authenticity + density
    return {
        "directness": directness,
        "rhythm": rhythm,
        "trust": trust,
        "authenticity": authenticity,
        "density": density,
        "total_score": total,
        "passed": total >= 35,
        "threshold": 35,
        "slop_hits": slop_hits,
        "thought_verb_hits": thought_verb_hits,
        "sentence_std_dev": stats["std_dev"],
    }


def build_split_model_narrative_directive(
    *,
    active_pov_id: str,
    character_name: str,
    mbti: str,
    next_pov_target: str,
    science_vegetable: str,
    colony_sol: int,
    tick_id: int,
    day_phase: str,
) -> dict[str, Any]:
    """Generate the Split-Model Pipeline directive (Model 1 Structural Outliner -> Model 2 Prose Executor)."""
    spine = CHARACTER_SPINES.get(active_pov_id, CHARACTER_SPINES["enclave_03_silas"])
    disaster_variant = CANONICAL_DISASTER_TYPES[(colony_sol + tick_id) % 3]  # FLAT_NO, YES_BUT, NO_AND_FURTHERMORE
    camouflage_tactic = CANONICAL_CAMOUFLAGE_TACTICS[(colony_sol * 2 + tick_id) % len(CANONICAL_CAMOUFLAGE_TACTICS)]
    return {
        "pipeline_architecture": "SPLIT_MODEL_OUTLINER_TO_EXECUTOR_V1",
        "stage_1_structural_outliner": {
            "character_spine": spine["spine"],
            "the_lie_believed": spine["lie_believed"],
            "the_truth_to_learn": spine["truth_to_learn"],
            "mamet_3_questions": {
                "who_wants_what": f"{character_name} ({mbti}) wants to stabilize {science_vegetable} before shift handoff to {next_pov_target}.",
                "what_happens_if_denied": "Cascading thermal/structural shear across the active sector and loss of Hearth ration margin.",
                "why_now": f"Sol {colony_sol} {day_phase} window closes in under 15 minutes.",
            },
            "swain_scene_beat": {
                "disaster_variant": disaster_variant,
                "macro_connector_to_sequel": "BUT",
                "macro_connector_to_next_scene": "THEREFORE",
            },
            "stanton_2_plus_2_rule": (
                "Plant two concrete sensory observations ('2 + 2') anchored to the mechanism and character spine; "
                "withhold the explicit '= 4' synthesis so the reader completes the equation."
            ),
            "knox_camouflage_tactic": camouflage_tactic,
        },
        "stage_2_prose_executor": {
            "palahniuk_thought_verb_ban": (
                "Unpack abstract thought verbs (knew, realized, felt, believed, remembered) into physical courtroom "
                "evidence, tool manipulation, and visceral MRUs (Stimulus -> Visceral Reflex -> Action -> Speech)."
            ),
            "le_guin_rhythm_target": "Maintain sentence-length standard deviation >= 5.0 words (mix winding technical clauses with 3-5 word percussive beats).",
            "three_pass_de_ai_rules": [
                "Pass 1 (Hemingway Iceberg): Never summarize the moral or theme at the end of a paragraph or scene.",
                "Pass 2 (Discourse Flow): Never use 'Rhetorical Question -> Immediate Self-Answer' ('Why? Because...').",
                "Pass 3 (Surface Calibration): Purge Pattern 30 (explaining metaphors), Pattern 31 (mic-drop fragments), and banned AI-isms (tapestry, testament, delve, cacophony, unwavering, shivers down spine).",
            ],
            "stop_slop_minimum_score": 35,
        },
    }
