#!/bin/bash
# Resource counts on the FHIR server. no-cache because HAPI caches searches for about a minute.
for t in Patient Encounter Observation QuestionnaireResponse; do
  printf '%s=%s ' $t "$(curl -s -H 'Cache-Control: no-cache' "localhost:8080/fhir/$t?_summary=count" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("total"))')"
done; echo
