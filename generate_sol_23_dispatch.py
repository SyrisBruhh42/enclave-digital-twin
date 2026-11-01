import json

dispatch = {
  "dispatch_id": "dispatch_sol_023",
  "tick_id": 92,
  "colony_sol": 23,
  "base_snapshot_tick": 92,
  "title": "Evening Dispatch Sol 23",
  "headline": "Evening Dispatch",
  "anchor_intro": "Vex sat on the roof, legs dangling over the edge.\nTo the east, the Red Giant was rising, a bloated, angry eye that bathed the world in crimson. To the west, the Blue Dwarf was setting, a piercing diamond that cast razor-sharp double shadows across the hand-built brass observatory roof. 'Calculates relativistic magnetohydrodynamic tides between a Red Giant and a Blue Dwarf while dangling his boots off the roof and complaining about stirring stew at 40 RPM,' he muttered to himself, adjusting a heavy copper coil. The bruised violet twilight offered a momentary reprieve from the relentless UV radiation, but the subterranean bioluminescent flora of the fungal canopy below pulsed with an agitated rhythm. We must defend the central induction core from the sheer kinetic friction of the atmospheric shear, attract the ambient static charge into our thermal reserves, and consume the resulting surplus to keep the mess hall running.",
  "broadcast_script": "Vex struck the side of his astrolabe, a hollow clang ringing out over the hum of the colony. 'Listen up, nodes. We've got a relativistic magnetohydrodynamic shear between the Red Giant's infrared coronal mass ejections and the Blue Dwarf's compressed ultraviolet bow shock incoming.' His tone was dry, practically bored, but his grip on the railing was white-knuckled. 'If you're complaining and no one is laughing, you're complaining wrong. Check your seals, ground your tools, and for the love of science, someone keep an eye on the hydroponics grid before we lose the entire yam crop.' Vex handed the physical baton to Terra, dropping the irreverent ironist mask for a fleeting second. 'Keep them safe.'",
  "broadcast_markdown": "# Evening Dispatch\n\nVex hands the baton to Terra.",
  "weather_report": "Relativistic magnetohydrodynamic shear between the Red Giant's infrared coronal mass ejections and the Blue Dwarf's compressed ultraviolet bow shock.",
  "quote_of_the_sol": "If you're complaining and no one is laughing, you're complaining wrong.",
  "newscaster_anchors": [
    "enclave_14_vex",
    "enclave_08_terra"
  ],
  "covered_day_phases": [
    "DAWN_SHIFT",
    "MIDDAY_EXPEDITION",
    "DUSK_CRAFT",
    "THE_FEAST"
  ],
  "lead_story": {
    "headline": "Enzymatic Chitin Tenderization under Ionization Storm",
    "summary": "Willow wrestles with enzymatic chitin tenderization under an ionization storm while Orion watches, resulting in a sudden burst of frantic protectiveness from the pragmatic alchemist.",
    "cited_event_ids": [
      "evt_s023_t0090_expedition_consequence"
    ],
    "actors": [
      "enclave_07_willow",
      "enclave_09_orion"
    ],
    "location": "Enclave_Crater_Valley",
    "day_phase": "MIDDAY_EXPEDITION",
    "salience_score": 0.85
  },
  "lpi_breakdown": {
    "loyalty": 0.75,
    "purpose": 0.8,
    "integration": 0.9,
    "composite_score": 0.81,
    "delta_from_previous_sol": 0.02
  }
}

with open("digests/daily/sol_023_dispatch.json", "w") as f:
    json.dump(dispatch, f, indent=2)
