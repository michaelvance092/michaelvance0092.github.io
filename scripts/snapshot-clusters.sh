#!/usr/bin/env bash
# scripts/snapshot-clusters.sh
# Export live cluster state, snapshot it, and commit the result to the site.
set -euo pipefail

CONTEXTS="${CONTEXTS:-$(kubectl config current-context)}"
OUT_DIR="${OUT_DIR:-assets/snapshots}"
STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
# Override if your plugin invocation differs.
SNAPSHOT_CMD="${SNAPSHOT_CMD:-kubectl kanvas snapshot}"

mkdir -p "$OUT_DIR"

for ctx in $CONTEXTS; do
  raw="$(mktemp)"
  kubectl --context "$ctx" get deployments,statefulsets,services,ingresses \
    --all-namespaces -o json > "$raw"

  # Keep the raw export beside the visual snapshot for later diffing.
  cp "$raw" "$OUT_DIR/${ctx}-${STAMP}.json"
  $SNAPSHOT_CMD "$raw"
  rm -f "$raw"
done

git add "$OUT_DIR"
git commit -s -m "snapshots: $STAMP" || echo "no changes to commit"
git push
