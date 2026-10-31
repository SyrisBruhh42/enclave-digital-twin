import json

with open("events/evt_s019_t0074_shadow_prank.json", "r") as f:
    proposal = json.load(f)

new_prop = {
    "event_id": proposal["event_id"],
    "tick_id": proposal["tick_id"],
    "colony_sol": proposal["colony_sol"],
    "day_phase": proposal["day_phase"],
    "world_timestamp_iso": proposal["world_timestamp_iso"],
    "base_snapshot_tick": proposal["base_snapshot_tick"],
    "event_type": proposal["event_type"],
    "location": proposal["location"],
    "actors": proposal["actors"],
    "summary": proposal["summary"],
    "importance": proposal["importance"],
    "novelty_score": proposal["novelty_score"],
    "science_vegetable": proposal["science_vegetable"],
    "state_deltas": proposal["state_deltas"],
    "relationship_deltas": proposal["relationship_deltas"],
    "evidence_refs": proposal["evidence_refs"],

    # Prank explicit root fields
    "prank_id": proposal["prank_id"],
    "origin_sol": proposal["origin_sol"],
    "maturity_sol": proposal["maturity_sol"],
    "node_a": proposal["node_a"],
    "node_b": proposal["node_b"],
    "node_c": proposal["node_c"],
    "target_b_missed": proposal["target_b_missed"],
    "blamed_node": proposal["blamed_node"],

    # Baton handoff
    "active_pov_id": proposal["active_pov_id"],
    "next_pov_target": proposal["next_pov_target"],
    "prev_next_pov_target": proposal["prev_next_pov_target"],

    # Other missing fields?
    "active_location": proposal["active_location"],
    "context_manifest": proposal["context_manifest"],
    "narrative_prose": proposal["narrative_prose"]
}
