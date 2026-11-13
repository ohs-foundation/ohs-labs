"""Load each slice into a FHIR server as its own patient, with IDs prefixed by the slice name.

Usage: python3 load_slices.py <server-base-url> <slices-dir> [synthea-org-bundles...]
The Synthea hospital and practitioner bundles go first, so conditional references resolve.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def post(base, bundle):
    req = urllib.request.Request(base, data=json.dumps(bundle).encode(),
                                 headers={"Content-Type": "application/fhir+json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        issues = json.loads(e.read()).get("issue", [])
        return f"{e.code} {[i.get('diagnostics', '')[:200] for i in issues][:2]}"


def as_transaction(slice_bundle, prefix):
    # Synthea links resources by urn:uuid fullUrls. Give each one a server id with the prefix.
    ids = {e["fullUrl"]: f'{e["resource"]["resourceType"]}/{prefix}-{e["resource"]["id"]}'
           for e in slice_bundle["entry"]}
    text = json.dumps(slice_bundle)
    for urn, ref in ids.items():
        text = text.replace(f'"{urn}"', f'"{ref}"')
    entries = []
    for e in json.loads(text)["entry"]:
        r = e["resource"]
        r["id"] = f'{prefix}-{r["id"]}'
        entries.append({"resource": r, "request": {"method": "PUT", "url": f'{r["resourceType"]}/{r["id"]}'}})
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def main(base, slices_dir, *org_bundles):
    for f in org_bundles:
        print(Path(f).name, post(base, json.load(open(f))))
    for f in sorted(Path(slices_dir).glob("visits-*.json")):
        prefix = f.stem.replace("visits-", "v")
        print(f.name, post(base, as_transaction(json.load(open(f)), prefix)))


if __name__ == "__main__":
    main(*sys.argv[1:])
