import json

with open("qa/sol_023_t0089_w23_b04_continuity_factcheck.json", "r") as f:
    data = json.load(f)

prose = """Jane wiped a smear of ionized mud from her forehead, glaring at the stubborn copper rod she was wrestling into the bedrock capacitor geode. She could model a planet-wide Lorenz strange attractor in phase space in her sleep, predicting exactly where the femtosecond laser-induced plasma channels would ionize a conductive step-leader highway at 50 kV/m atmospheric potential gradient. Yet here she was, spending her afternoon digging a muddy trench by hand.

A violet laser needle stitched the bruised purple thunderhead to a screaming copper spire fifty meters above the valley, the air thick with ozone and static. She braced herself against the trench wall, forcing the heavy rod down. She hated manual labor, she really did. It felt inefficient. But as the sky above rumbled, demanding to discharge, she realized that sometimes the most elegant equation had to be solved with a hammer.

She felt her mind straining, the urge to demand someone applaud her brilliant calculation of the strike zone rising—a flare of Leo diva energy—but she shoved it down. "If you're complaining and no one is laughing, you're complaining wrong," she muttered to herself, echoing Hector's obnoxious advice.

She drove the rod home just as the potential gradient spiked. Now, she just needed Willow to synthesize the epoxy-sap to seal the junction before the rain started. She pulled herself out of the mud, clutching her toolkit, and headed for the greenhouse."""

data["dual_agent_contract"]["master_narrator"]["agency_handoff_prompt"] = prose

with open("qa/sol_023_t0089_w23_b04_continuity_factcheck.json", "w") as f:
    json.dump(data, f, indent=2)
