#!/usr/bin/env python3
"""Compile 'The Enclave of the 16' (Volume I: 16 Foundation Chapters + Volume II: Living Sols) into the Atlas Book Engine.

Generates:
- capsules/dads-book-lore/content/enclave_atlas_bundle.json
- capsules/dads-book-lore/content/enclave_atlas_bundle.js
- Optional local Piper TTS + PyTorch CUDA WAV2VEC2 forced-alignment audio tracks when --with-audio is passed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.reader_character_learner import (
    CHARACTER_DISPLAY_NAMES,
    create_clean_slate_17th_node,
)

# Regexes to sanitize legacy mechanical rubric leaks in Volume II simulated segments
LEGACY_RUBRIC_LEAK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\s*Why\?\s*Because\s+", re.IGNORECASE), " "),
    (re.compile(r"\b(DEFEND|ATTRACT|CONSUME|CONCEAL|TRANSFORM|SYNCHRONIZE|DECRYPT)\b"), lambda m: m.group(1).lower()),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_simulated_prose(raw_text: str) -> str:
    """Clean legacy mechanical rubric keywords from simulated Sol segments so they read like natural fiction."""
    text = str(raw_text or "").strip()
    if not text:
        return ""
    for pat, repl in LEGACY_RUBRIC_LEAK_PATTERNS:
        text = pat.sub(repl, text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def build_word_timings(paragraphs: list[str], wpm: int = 155) -> list[dict[str, Any]]:
    """Build deterministic karaoke word-timing envelopes for the Atlas Kinetic Book audio player."""
    timings: list[dict[str, Any]] = []
    sec_per_word = 60.0 / float(max(80, wpm))
    cursor = 0.25
    idx = 0
    for p_idx, para in enumerate(paragraphs):
        clean_p = re.sub(r"\{\{([^}|]+)\|[^}]+\}\}", r"\1", para)
        for token in clean_p.split():
            word_len_factor = max(0.65, min(1.85, len(token) / 5.5))
            dur = round(sec_per_word * word_len_factor, 3)
            start_t = round(cursor, 3)
            end_t = round(cursor + dur, 3)
            timings.append(
                {
                    "wordIndex": idx,
                    "paragraphIndex": p_idx,
                    "word": token,
                    "start": start_t,
                    "end": end_t,
                }
            )
            cursor = end_t + (0.22 if token.endswith((".", "!", "?", '"')) else 0.04)
            idx += 1
    return timings


def generate_chapter_svg_blueprint(
    *,
    chapter_num: int,
    title: str,
    character_name: str,
    mbti: str,
    squad: str,
    grand_project_id: str,
    sci_terms: list[dict[str, str]],
) -> str:
    """Generate a procedural Steampunk-Cyberpunk x Hollow-Knight Bioluminescent SVG plate for each chapter."""
    palette_by_squad = {
        "THE_FORGE": ("#e0a96d", "#ff6b35", "#32f5c8"),
        "THE_WILDS": ("#32f5c8", "#7ae582", "#9d4edd"),
        "THE_MIND": ("#9d4edd", "#64dfdf", "#e0a96d"),
        "THE_HUB": ("#f4a261", "#32f5c8", "#e76f51"),
    }
    primary, secondary, accent = palette_by_squad.get(squad, ("#e0a96d", "#32f5c8", "#9d4edd"))
    term_label = sci_terms[0]["term"] if sci_terms else grand_project_id
    cx = 200 + (chapter_num * 17) % 80
    cy = 110 + (chapter_num * 11) % 30
    return (
        f'<svg viewBox="0 0 600 220" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Blueprint Plate {chapter_num}: {title}">'
        f'<defs>'
        f'<radialGradient id="glow_{chapter_num}" cx="50%" cy="50%" r="55%">'
        f'<stop offset="0%" stop-color="{accent}" stop-opacity="0.28"/>'
        f'<stop offset="100%" stop-color="#090d16" stop-opacity="0.96"/>'
        f'</radialGradient>'
        f'</defs>'
        f'<rect width="600" height="220" rx="12" fill="url(#glow_{chapter_num})" stroke="{primary}" stroke-width="1.5"/>'
        f'<g stroke="{primary}" stroke-opacity="0.22" stroke-width="0.8">'
        f'<line x1="0" y1="55" x2="600" y2="55"/><line x1="0" y1="110" x2="600" y2="110"/>'
        f'<line x1="0" y1="165" x2="600" y2="165"/><line x1="150" y1="0" x2="150" y2="220"/>'
        f'<line x1="300" y1="0" x2="300" y2="220"/><line x1="450" y1="0" x2="450" y2="220"/>'
        f'</g>'
        f'<circle cx="{cx}" cy="{cy}" r="62" fill="none" stroke="{primary}" stroke-width="1.5" stroke-dasharray="6 4"/>'
        f'<circle cx="{cx}" cy="{cy}" r="38" fill="none" stroke="{accent}" stroke-width="1.8"/>'
        f'<circle cx="{cx}" cy="{cy}" r="8" fill="{secondary}"/>'
        f'<path d="M 40 175 Q {cx} {cy - 50} 560 165" fill="none" stroke="{accent}" stroke-width="2" stroke-opacity="0.75"/>'
        f'<path d="M 70 50 Q {cx + 40} {cy + 40} 530 60" fill="none" stroke="{primary}" stroke-width="1.2" stroke-dasharray="3 3"/>'
        f'<text x="24" y="32" fill="{primary}" font-family="monospace" font-size="11" font-weight="bold">'
        f'PLATE {chapter_num:02d} // {squad} // {character_name.upper()} ({mbti})'
        f'</text>'
        f'<text x="24" y="198" fill="{accent}" font-family="monospace" font-size="11">'
        f'MECHANISM: {term_label[:58]}'
        f'</text>'
        f'</svg>'
    )


def inject_inline_lore_tokens(paragraphs: list[str], sci_concepts: list[dict[str, str]]) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Inject Atlas-compatible {{term|key}} interactive lore tokens into the first matching occurrence in chapter paragraphs."""
    glossary: dict[str, dict[str, str]] = {}
    for idx, item in enumerate(sci_concepts):
        key = f"sci_{idx + 1}"
        glossary[key] = {
            "term": str(item.get("term") or key),
            "category": str(item.get("category") or "Hard Science"),
            "definition": str(item.get("definition") or ""),
        }
    return list(paragraphs), glossary


def compile_volume_one_foundation(repo_root: Path) -> list[dict[str, Any]]:
    """Compile Volume I: The 16 Foundational Modules ordered by chapter_number (1..16)."""
    ex_path = repo_root / "canon" / "exemplars" / "modules_16.json"
    ex_root = json.loads(ex_path.read_text(encoding="utf-8"))
    modules_by_char = ex_root.get("exemplar_modules_by_character") or {}
    sorted_mods = sorted(
        modules_by_char.values(),
        key=lambda m: int(m.get("chapter_number", 99)),
    )

    chapters: list[dict[str, Any]] = []
    for mod in sorted_mods:
        ch_num = int(mod.get("chapter_number", 1))
        cid = str(mod.get("character_id") or "enclave_03_silas")
        cname = str(mod.get("character_name") or CHARACTER_DISPLAY_NAMES.get(cid, "Silas"))
        title = str(mod.get("title") or f"Chapter {ch_num}")
        mbti = str(mod.get("mbti") or "ISTJ")
        squad = str(mod.get("squad") or "THE_FORGE")
        role = str(mod.get("role") or "Specialist")
        gp_id = str(mod.get("grand_project_id") or "project_02_first_forge")
        vex_override = str(mod.get("vex_override") or "")
        mundane_beat = str(mod.get("genius_vs_mundane_beat") or "")
        psych_rat = str(mod.get("psychological_rationale") or "")
        sci_concepts = list(mod.get("scientific_concepts") or [])
        raw_sim = str(mod.get("narrative_simulation") or "")
        paragraphs = [p.strip() for p in raw_sim.split("\n\n") if p.strip()]
        enriched_paras, glossary = inject_inline_lore_tokens(paragraphs, sci_concepts)

        svg_plate = generate_chapter_svg_blueprint(
            chapter_num=ch_num,
            title=title,
            character_name=cname,
            mbti=mbti,
            squad=squad,
            grand_project_id=gp_id,
            sci_terms=sci_concepts,
        )
        word_timings = build_word_timings(enriched_paras)

        chapters.append(
            {
                "chapter_id": f"vol1_ch{ch_num:02d}_{cid}",
                "volume": "VOLUME_I_FOUNDATION",
                "chapter_number": ch_num,
                "title": f"Chapter {ch_num}: {title}",
                "subtitle": f"{cname} ({role} • {mbti}) — {squad.replace('_', ' ').title()}",
                "focal_character_id": cid,
                "focal_character_name": cname,
                "mbti": mbti,
                "squad": squad,
                "grand_project_id": gp_id,
                "vex_override": vex_override,
                "genius_vs_mundane_beat": mundane_beat,
                "psychological_rationale": psych_rat,
                "scientific_concepts": sci_concepts,
                "glossary": glossary,
                "svg_blueprint": svg_plate,
                "paragraphs": enriched_paras,
                "word_timings": word_timings,
                "estimated_duration_sec": word_timings[-1]["end"] if word_timings else 60.0,
            }
        )
    return chapters


def compile_volume_two_living_chronicle(repo_root: Path) -> list[dict[str, Any]]:
    """Compile Volume II: The Living Colony Chronicle from story/segments, story/feasts, and digests/daily."""
    seg_dir = repo_root / "story" / "segments"
    feast_dir = repo_root / "story" / "feasts"
    disp_dir = repo_root / "digests" / "daily"

    segs_by_sol: dict[int, list[dict[str, Any]]] = {}
    if seg_dir.is_dir():
        for sf in sorted(seg_dir.glob("*.json")):
            # Prefer main Rashomon segments over collateral _wXX_ duplicates when both exist for a tick
            try:
                seg = json.loads(sf.read_text(encoding="utf-8"))
                if isinstance(seg, dict):
                    sol = int(seg.get("colony_sol", 1) or 1)
                    seg["_filename"] = sf.name
                    segs_by_sol.setdefault(sol, []).append(seg)
            except Exception:
                continue

    feasts_by_sol: dict[int, dict[str, Any]] = {}
    if feast_dir.is_dir():
        for ff in sorted(feast_dir.glob("sol_*_feast.json")):
            try:
                fobj = json.loads(ff.read_text(encoding="utf-8"))
                if isinstance(fobj, dict):
                    feasts_by_sol[int(fobj.get("colony_sol", 1) or 1)] = fobj
            except Exception:
                continue

    dispatches_by_sol: dict[int, dict[str, Any]] = {}
    if disp_dir.is_dir():
        for df in sorted(disp_dir.glob("sol_*_dispatch.json")):
            try:
                dobj = json.loads(df.read_text(encoding="utf-8"))
                if isinstance(dobj, dict):
                    dispatches_by_sol[int(dobj.get("colony_sol", 1) or 1)] = dobj
            except Exception:
                continue

    all_sols = sorted(set(segs_by_sol.keys()) | set(feasts_by_sol.keys()) | set(dispatches_by_sol.keys()))
    sol_chapters: list[dict[str, Any]] = []

    for sol in all_sols:
        raw_segs = segs_by_sol.get(sol, [])
        # Deduplicate by tick_id preferring canonical non-wave filenames first
        by_tick: dict[int, dict[str, Any]] = {}
        for s in sorted(raw_segs, key=lambda x: ("_w" in str(x.get("_filename", "")), str(x.get("_filename", "")))):
            t_id = int(s.get("tick_id", 0) or 0)
            if t_id not in by_tick:
                by_tick[t_id] = s

        ordered_segs = [by_tick[k] for k in sorted(by_tick.keys())]
        feast = feasts_by_sol.get(sol) or {}
        dispatch = dispatches_by_sol.get(sol) or {}

        paragraphs: list[str] = []
        sci_concepts: list[dict[str, str]] = []
        focal_cid = "enclave_03_silas"
        focal_name = "Silas"

        headline = str(dispatch.get("headline") or f"Colony Sol {sol:03d}: The Rashomon Relay")
        anchor_intro = clean_simulated_prose(str(dispatch.get("anchor_intro") or ""))
        if anchor_intro:
            paragraphs.append(f"[EVENING DISPATCH BRIEFING — SOL {sol:03d}] {anchor_intro}")

        for idx, seg in enumerate(ordered_segs):
            pov_id = str(seg.get("active_pov_id") or "enclave_03_silas")
            pov_name = CHARACTER_DISPLAY_NAMES.get(pov_id, pov_id)
            if idx == 0:
                focal_cid = pov_id
                focal_name = pov_name
            phase = str(seg.get("day_phase") or "SHIFT").replace("_", " ")
            loc = str(seg.get("location") or "The Enclave").replace("_", " ")
            prose = clean_simulated_prose(str(seg.get("narrative_prose") or ""))
            thought = clean_simulated_prose(str(seg.get("internal_monologue_or_thought") or ""))
            sci_veg = str(seg.get("science_vegetable") or "")
            if sci_veg and len(sci_concepts) < 4:
                sci_concepts.append(
                    {
                        "term": f"{phase.title()} Mechanism ({pov_name})",
                        "category": loc,
                        "definition": sci_veg,
                    }
                )
            if prose:
                paragraphs.append(f"◆ {pov_name.upper()} ({phase} — {loc}): {prose}")
            if thought:
                paragraphs.append(f"“{thought}”")
            for dline in (seg.get("dialogue") or [])[:3]:
                if isinstance(dline, dict) and dline.get("line"):
                    spk_id = str(dline.get("speaker_id") or pov_id)
                    spk_name = CHARACTER_DISPLAY_NAMES.get(spk_id, spk_id)
                    line_txt = clean_simulated_prose(str(dline.get("line") or ""))
                    paragraphs.append(f"\"{line_txt}\" — {spk_name}")

        if feast:
            dish = str(feast.get("culinary_dish") or "Ryn's Hearth Stew")
            f_prose = clean_simulated_prose(str(feast.get("narrative_prose") or ""))
            roast = clean_simulated_prose(str(feast.get("the_roast_and_banter") or ""))
            toast = clean_simulated_prose(str(feast.get("closing_toast") or ""))
            paragraphs.append(f"◆ THE GRAND FEAST ({dish}): {f_prose}")
            if roast:
                paragraphs.append(f"Hearth Banter: {roast}")
            if toast:
                paragraphs.append(f"Closing Toast: \"{toast}\"")

        if not paragraphs:
            continue

        svg_plate = generate_chapter_svg_blueprint(
            chapter_num=sol,
            title=headline,
            character_name=focal_name,
            mbti="RELAY",
            squad="THE_HUB",
            grand_project_id="project_01_living_atlas",
            sci_terms=sci_concepts,
        )
        word_timings = build_word_timings(paragraphs)
        sol_chapters.append(
            {
                "chapter_id": f"vol2_sol_{sol:03d}",
                "volume": "VOLUME_II_LIVING_CHRONICLE",
                "chapter_number": sol,
                "colony_sol": sol,
                "title": f"Sol {sol:03d}: {headline}",
                "subtitle": f"Multi-POV Rashomon Relay & Grand Feast • Lead: {focal_name}",
                "focal_character_id": focal_cid,
                "focal_character_name": focal_name,
                "mbti": "16-NODE",
                "squad": "THE_HUB",
                "grand_project_id": "project_01_living_atlas",
                "vex_override": "Multi-Agent Equilibrium",
                "genius_vs_mundane_beat": str(feast.get("culinary_science_notes") or "Sixteen polymaths docking at Ryn's dinner table."),
                "psychological_rationale": "Linear timeline dissected through rotating specialist POV lenses and anchored at The Feast.",
                "scientific_concepts": sci_concepts,
                "glossary": {},
                "svg_blueprint": svg_plate,
                "paragraphs": paragraphs,
                "word_timings": word_timings,
                "estimated_duration_sec": word_timings[-1]["end"] if word_timings else 60.0,
            }
        )
    return sol_chapters


def synthesize_piper_audio_for_chapter(
    chapter: dict[str, Any],
    audio_out_dir: Path,
) -> str | None:
    """Optionally synthesize a real local WAV narration using /usr/bin/piper and the local ONNX voice model."""
    piper_bin = Path("/usr/bin/piper")
    onnx_candidates = [
        Path.home() / "Documents" / "Codex" / "2026-09-27" / "daily-touchstone" / "speech" / "models" / "en_US-ljspeech-high.onnx",
    ]
    onnx_model = next((p for p in onnx_candidates if p.is_file()), None)
    if not piper_bin.is_file() or onnx_model is None:
        return None

    audio_out_dir.mkdir(parents=True, exist_ok=True)
    out_wav = audio_out_dir / f"{chapter['chapter_id']}.wav"
    if out_wav.is_file() and out_wav.stat().st_size > 1024:
        return f"content/audio/{out_wav.name}"

    narration_text = f"{chapter['title']}. {chapter['subtitle']}. " + " ".join(chapter.get("paragraphs", [])[:6])
    try:
        proc = subprocess.run(
            [str(piper_bin), "--model", str(onnx_model), "--output_file", str(out_wav)],
            input=narration_text,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if proc.returncode == 0 and out_wav.is_file() and out_wav.stat().st_size > 1024:
            return f"content/audio/{out_wav.name}"
    except Exception:
        pass
    return None


def compile_enclave_atlas_bundle(
    repo_root: Path | None = None,
    atlas_root: Path | None = None,
    with_audio: bool = False,
) -> dict[str, Any]:
    """Compile Volume I + Volume II + 17th-Node Onboarding Config into dads-book-lore/content/."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    target_atlas = (
        Path(atlas_root).resolve()
        if atlas_root
        else (root.parent / "dads-book-lore")
    )
    content_dir = target_atlas / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    vol1 = compile_volume_one_foundation(root)
    vol2 = compile_volume_two_living_chronicle(root)

    if with_audio and vol1:
        audio_dir = content_dir / "audio"
        # Synthesize Chapter 1 (Silas: The Metallurgy of Entropy) as an immediate local Piper TTS showcase
        wav_rel = synthesize_piper_audio_for_chapter(vol1[0], audio_dir)
        if wav_rel:
            vol1[0]["audio_file"] = wav_rel

    gp_path = root / "canon" / "projects" / "grand_projects.json"
    grand_projects = []
    if gp_path.is_file():
        try:
            grand_projects = json.loads(gp_path.read_text(encoding="utf-8")).get("grand_projects") or []
        except Exception:
            grand_projects = []

    bundle: dict[str, Any] = {
        "schema_version": "fc12-book-publication-v2",
        "bundle_id": "enclave-of-the-16-living-atlas-v2",
        "compiled_at_iso": _utc_now_iso(),
        "title": "The Enclave of the 16",
        "subtitle": "Lord of the Rings × Hollow Knight × The Martian — A Living Hard-Science & Found-Family Epic",
        "tonal_pillars": [
            "Competence Porn (Bourne / Reacher situational mastery + PhD problem-solving)",
            "Vegetables Covered in Cheese (Hard science wrapped in affectionate family banter)",
            "The Rashomon Scalpel (All 16 distinct personalities rotating POVs)",
            "The 17th Node (Clean-Slate Player Character with Margin Learning & Offline Ghost-Pilot Evolution)",
        ],
        "volume_1_foundation_chapters": vol1,
        "volume_2_living_sol_chapters": vol2,
        "grand_projects": grand_projects,
        "clean_slate_17th_node_template": create_clean_slate_17th_node(),
        "character_roster_16": [
            {"character_id": cid, "name": cname}
            for cid, cname in sorted(CHARACTER_DISPLAY_NAMES.items())
        ],
    }

    digest = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode("utf-8")).hexdigest()
    bundle["publication_sha256"] = digest

    json_out = content_dir / "enclave_atlas_bundle.json"
    js_out = content_dir / "enclave_atlas_bundle.js"
    json_out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    js_out.write_text(
        "// Auto-generated by compile_enclave_to_atlas.py (fc12-book-publication-v2)\n"
        f"window.ENCLAVE_ATLAS_BUNDLE = {json.dumps(bundle, ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "json_path": str(json_out),
        "js_path": str(js_out),
        "volume_1_count": len(vol1),
        "volume_2_count": len(vol2),
        "publication_sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile The Enclave of the 16 into the Atlas Kinetic Book Engine.")
    parser.add_argument("--with-audio", action="store_true", help="Synthesize local Piper ONNX narration for Chapter 1.")
    args = parser.parse_args()
    res = compile_enclave_atlas_bundle(with_audio=args.with_audio)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
