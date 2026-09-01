#!/usr/bin/env bash
# Builds the scaffold templates in harness/templates/ from the committed
# sources in harness/template-src/ - run once after cloning the repo.
# Existing templates are left untouched (delete one to rebuild it).
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"

build() {  # $1 template name  $2 source tree
  local NAME="$1"
  local SRC="$2"
  local DST="$H/templates/$NAME"
  if [ -d "$DST/.git" ]; then
    echo "template $NAME exists, skipping"
    return
  fi
  rm -rf "$DST"
  mkdir -p "$DST"
  cp -R "$H/template-src/$SRC/." "$DST/"
  case "$NAME" in
    ohs-skills-claude)
      mkdir -p "$DST/.claude/skills"
      cp -R "$H/../skills/kotlin-fhir" "$H/../skills/kotlin-fhir-engine" \
            "$H/../skills/kotlin-fhir-data-capture" "$DST/.claude/skills/"
      ;;
    ohs-skills-gemini)
      python3 - "$H/../skills" "$DST/GEMINI.md" <<'PY'
import sys
sk, dst = sys.argv[1], sys.argv[2]
out = ["# OHS library guide\n\nDocumentation for the three OHS FHIR libraries this project uses.\n"]
for name in ("kotlin-fhir", "kotlin-fhir-engine", "kotlin-fhir-data-capture"):
    t = open(f"{sk}/{name}/SKILL.md").read()
    if t.startswith("---"):
        t = t.split("---", 2)[2]
    out.append(t.strip() + "\n")
open(dst, "w").write("\n".join(out))
PY
      ;;
  esac
  git -C "$DST" init -q
  git -C "$DST" add -A
  git -C "$DST" commit -q -m "baseline ($NAME, built by setup-templates.sh)"
  chmod +x "$DST/gradlew" 2>/dev/null || true
  echo "built template $NAME"
}

build cold cold
build ohs ohs
build ohs-skills-claude ohs
build ohs-skills-gemini ohs
echo "done. Cache-warm once: (cd templates/cold && ./gradlew -q :app:assembleDebug); same for ohs."
