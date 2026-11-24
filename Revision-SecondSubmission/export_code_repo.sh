#!/usr/bin/env bash
# Build the public code repository (github.com/boldip/AidGraph) from the two code folders of
# the private working repository. Copies tracked and untracked-but-not-ignored files of
# SecondSubmission/ and Revision-SecondSubmission/, minus paper sources, reviews, logs,
# paper-patching scripts and caches; adds the top-level README and commits the tree as one
# commit (no history). Usage: export_code_repo.sh [TARGET_DIR] [--push]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/.." && pwd)
TARGET=${1:-$REPO/../AidGraph}
PUSH=${2:-}
mkdir -p "$TARGET"; TARGET=$(cd "$TARGET" && pwd)

cd "$REPO"
{ git ls-files; git ls-files -o --exclude-standard; } | sort -u \
  | grep -E '^(SecondSubmission|Revision-SecondSubmission)/' \
  | grep -vE '(^|/)(paper|site|audit_page|logs_A|__pycache__|store)/' \
  | grep -vE '\.(pyc|log|bak|pdf)$' \
  | grep -vE '(^|/)(reviews\.txt|mail[0-9]*\.txt|paul-[0-9A-Za-z]*\.txt|NOTE-FOR-COAUTHORS\.md)$' \
  | grep -vE '^Revision-SecondSubmission/(NOTE-FOR-COAUTHORS\.md|AidGraph-README\.md|AidGraph-LICENSE|r5_patch_paper\.py|r10[bc]?_patch_[a-z0-9]+\.py|run_A_rest\.sh)$' \
  | grep -vE '^SecondSubmission/(report\.tex|mail4\.pdf|DONE_A|FAILED_A|run_A_resume[0-9]*\.sh|Aid_Graph.*\.pdf)$' \
  > "$TARGET/.export-list"
while read -r f; do [ -e "$f" ] || { echo "missing $f" >&2; exit 1; }; done < "$TARGET/.export-list"
rsync -a --delete --files-from="$TARGET/.export-list" --exclude=.git "$REPO/" "$TARGET/"
cp "$HERE/AidGraph-README.md" "$TARGET/README.md"
cp "$HERE/AidGraph-LICENSE" "$TARGET/LICENSE"
cp "$REPO/SecondSubmission/.gitignore" "$TARGET/SecondSubmission/.gitignore" 2>/dev/null || true
rm -f "$TARGET/.export-list"
echo "exported $(find "$TARGET" -type f -not -path '*/.git/*' | wc -l) files to $TARGET"

cd "$TARGET"
[ -d .git ] || git init -q -b main
git remote get-url origin >/dev/null 2>&1 || git remote add origin git@github.com:boldip/AidGraph.git
git add -A
if git diff --cached --quiet; then echo "nothing to commit"; else
git commit -q -F - <<'MSG'
Analysis code for "The Hidden Geometry of Global Aid" (second-round revision)

Single-commit export of the two code folders of the working repository:
the main pipeline (SecondSubmission/) and the revision analyses
(Revision-SecondSubmission/), with derived outputs and documentation.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SsXz62gM6Kakwy9X2ht1ZU
MSG
git log --oneline -1; fi
if [ "$PUSH" = "--push" ]; then git push -u origin main; fi
