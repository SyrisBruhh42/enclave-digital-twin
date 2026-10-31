import sys
from pathlib import Path
import json

REPO_ROOT = Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

from tools.check_enclave_constitutions import validate_showrunner_storytelling_contract, validate_proposal

with open("story/segments/seg_s021_t0081_enclave_03_silas.json") as f:
    proposal = json.load(f)

result = validate_proposal(proposal, repo_root=REPO_ROOT)
print("Validate proposal laws:", result["violated_laws"])
print("Validate proposal errors:", result["errors"])
