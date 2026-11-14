#!/bin/bash
# Run every mechanical rule shipped by the repository's skills.
#
# A skill may ship `scripts/lint_*.py`. Each rule checks structured data, paths,
# graph metadata, or a generated artifact. It does not judge authored skill prose:
# whether a surface has taken back a verdict, whether a stance is seeded with
# its author's findings, or whether an argument is good is a semantic review
# question, not a string match. prek runs this on every commit, so structural
# rules fire on every change instead of only when someone remembers.
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
