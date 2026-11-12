#!/bin/bash
# Validate every SKILL.md in this repository using the vendored quick validator.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATE_SCRIPT="$ROOT_DIR/scripts/quick_validate.py"

if [ ! -f "$VALIDATE_SCRIPT" ]; then
    echo "Missing validator script: $VALIDATE_SCRIPT"
    exit 1
fi

# The published meta skills live in `skills/`; the worked examples demonstrate
# installing a stance set into a target project's `.agents/skills/`.
SKILLS_DIRS=(
    "$ROOT_DIR/skills"
    "$ROOT_DIR"/examples/*/.agents/skills
)

FAILED=0
FOUND=0
for dir in "${SKILLS_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    for skill in "$dir"/*/; do
        [ -f "$skill/SKILL.md" ] || continue
        FOUND=$((FOUND + 1))
        echo "--- ${skill#"$ROOT_DIR"/} ---"
        if ! python3 "$VALIDATE_SCRIPT" "$skill"; then
            FAILED=1
        fi
    done
done

if [ "$FOUND" -eq 0 ]; then
    echo "No SKILL.md files found"
    exit 0
fi

echo "Checked $FOUND skill(s)"
exit $FAILED
