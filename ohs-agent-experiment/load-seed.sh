#!/usr/bin/env bash
# Loads the ANC seed bundle into the local HAPI FHIR server.
# Usage: ./load-seed.sh   (override the target with FHIR_BASE=http://... ./load-seed.sh)
set -euo pipefail

BASE="${FHIR_BASE:-http://localhost:8080/fhir}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Waiting for HAPI at $BASE (first boot can take a minute or two)..."
for i in $(seq 1 60); do
  if curl -sf "$BASE/metadata" > /dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "Server did not come up after 5 minutes. Check: docker compose logs hapi" >&2
    exit 1
  fi
  sleep 5
done
echo "Server is up. Posting seed bundle..."

RESPONSE="$(curl -s -X POST \
  -H "Content-Type: application/fhir+json" \
  --data @"$DIR/seed/anc-seed-bundle.json" \
  "$BASE")"

if echo "$RESPONSE" | grep -q '"resourceType": *"OperationOutcome"' && ! echo "$RESPONSE" | grep -q '"type": *"transaction-response"'; then
  echo "Seed load FAILED. Server response:" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

echo "Seed bundle accepted. Verifying..."
for TYPE in Patient Encounter Observation Questionnaire; do
  COUNT="$(curl -s "$BASE/$TYPE?_summary=count" | sed -n 's/.*"total" *: *\([0-9]*\).*/\1/p')"
  echo "  $TYPE: $COUNT"
done
echo "Done. Expected: Patient 3, Encounter 3, Observation 12, Questionnaire 1."
