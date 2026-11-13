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
# installing a stance set into a target project's `.agents/skills/`. Both are
# found by walking the tree, so a new directory needs no edit here.

FAILED=0
FOUND=0
while IFS= read -r skill_md; do
    skill="$(dirname "$skill_md")"
    rel="${skill#"$ROOT_DIR"/}"
    FOUND=$((FOUND + 1))
    echo "--- $rel ---"
    if ! python3 "$VALIDATE_SCRIPT" "$skill"; then
        FAILED=1
    fi
    # `lint_*.py` is a mechanical rule, not review guidance: prek runs it on
    # every commit, so it must be executable and must pass its own check.
    for lint in "$skill"/scripts/lint_*.py; do
        [ -f "$lint" ] || continue
        if [ ! -x "$lint" ]; then
            echo "$rel: $(basename "$lint") is not executable"
            FAILED=1
        elif ! python3 "$lint" --self-test; then
            echo "$rel: $(basename "$lint") failed its self-test"
            FAILED=1
        fi
    done
done < <(
    find "$ROOT_DIR/skills" "$ROOT_DIR"/examples/*/.agents/skills \
        -name SKILL.md -type f 2>/dev/null | sort
)

if [ "$FOUND" -eq 0 ]; then
    echo "No SKILL.md files found"
    exit 0
fi

echo "Checked $FOUND skill(s)"
exit $FAILED
