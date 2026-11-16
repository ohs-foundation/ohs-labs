"""Cut one Synthea patient into growing FHIR bundles: the Patient plus their N most recent visits
(Encounters) and every clinical resource recorded at those visits. Each bundle is self-contained:
anything a resource points to (a condition from an older visit, a Medication) is pulled in too.

Usage: python3 make_slices.py <synthea-patient.json> <out-dir>
"""
import json
import re
import sys
from pathlib import Path

# The resource types Tokempic's built-in views cover. Billing (Claim, ExplanationOfBenefit)
# and base64 documents are left out, so every format carries the same information.
CLINICAL = {"Observation", "Condition", "Procedure", "Immunization", "MedicationRequest", "AllergyIntolerance"}
VISITS = [1, 2, 5, 10, 20, 40]


def main(src, out):
    entries = json.load(open(src))["entry"]
    by_url = {e["fullUrl"]: e for e in entries}
    patient = next(e for e in entries if e["resource"]["resourceType"] == "Patient")
    encounters = [e for e in entries if e["resource"]["resourceType"] == "Encounter"]
    encounters.sort(key=lambda e: e["resource"]["period"]["start"], reverse=True)
    by_encounter = {}
    for e in entries:
        r = e["resource"]
        if r["resourceType"] in CLINICAL and "encounter" in r:
            by_encounter.setdefault(r["encounter"]["reference"], []).append(e)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("slice-*.json"):
        old.unlink()
    for n in [v for v in VISITS if v < len(encounters)] + [len(encounters)]:
        visits = encounters[:n]
        rest = [x for v in visits for x in by_encounter.get(v["fullUrl"], [])]
        chosen = [patient] + visits + rest
        have = {e["fullUrl"] for e in chosen}
        while True:
            missing = set(re.findall(r'"(urn:uuid:[0-9a-f-]+)"', json.dumps(chosen))) - have
            missing &= by_url.keys()
            if not missing:
                break
            chosen += [by_url[u] for u in sorted(missing)]
            have |= missing
        rest = chosen[1 + len(visits):]
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": chosen}
        name = f"visits-{n:02d}"
        (out / f"{name}.json").write_text(json.dumps(bundle))
        print(f"{name}: {n} visits, {n + len(rest)} resources")


if __name__ == "__main__":
    main(*sys.argv[1:3])
