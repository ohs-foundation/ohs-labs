#!/usr/bin/env bash
# Rebuild the two skills templates from the current skills/ folder.
# Run this whenever a skill in ohs-agent-experiment/skills/ changes, so the
# runner picks it up. setup-templates.sh skips templates that already exist,
# so editing skills/ alone does NOT reach the runner - this deletes the two
# skills templates first, then rebuilds only those.
# The cold and ohs templates are left untouched (they carry no skills, and
# rebuilding them would discard their warm Gradle cache).
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"

rm -rf "$H/templates/ohs-skills-claude" "$H/templates/ohs-skills-gemini"
"$H/setup-templates.sh"

echo
echo "Verifying the rebuilt templates match skills/ ..."
CLAUDE_SKILLS="$H/templates/ohs-skills-claude/.claude/skills"
ok=1
for s in kotlin-fhir kotlin-fhir-engine kotlin-fhir-data-capture; do
  if diff -q "$H/../skills/$s/SKILL.md" "$CLAUDE_SKILLS/$s/SKILL.md" >/dev/null; then
    echo "  ok   claude/$s"
  else
    echo "  DRIFT claude/$s"; ok=0
  fi
done
[ -s "$H/templates/ohs-skills-gemini/GEMINI.md" ] && echo "  ok   gemini/GEMINI.md" || { echo "  MISSING gemini/GEMINI.md"; ok=0; }

echo
if [ "$ok" = 1 ]; then
  echo "Templates are current. Reminder: a skill change is a new treatment"
  echo "version - bump skills/README.md and do not pool new ohs-skills runs"
  echo "with older ones when comparing cells."
else
  echo "One or more templates did not match skills/ - inspect before running." >&2
  exit 1
fi
