#!/bin/bash
# Run every mechanical rule in the repository's stance skills.
#
# A skill may ship `scripts/lint_*.py`. Each is a rule that would
# otherwise be a paragraph of guidance: a stance seeded with its author's
# findings, a ledger pointing at a file no clone contains. prek runs this on
# every commit, so the rule fires on every change instead of only when someone
# remembers to read the paragraph.
#
# Each rule takes the changed files and exits non-zero on a violation. It must
# also pass its own `--self-test`, which `validate-skills.sh` enforces, so a
# rule that stops firing is caught by the same gate that runs it.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# prek passes the staged files; without arguments, check the whole repository.
if [ "$#" -eq 0 ]; then
    set -- "$ROOT_DIR"
fi

FAILED=0
FOUND=0
while IFS= read -r rule; do
    FOUND=$((FOUND + 1))
    echo "--- ${rule#"$ROOT_DIR"/} ---"
    if ! python3 "$rule" "$@"; then
        FAILED=1
    fi
done < <(find "$ROOT_DIR/skills" -name 'lint_*.py' -type f 2>/dev/null | sort)

if [ "$FOUND" -eq 0 ]; then
    echo "No lint rules found"
fi

exit $FAILED
