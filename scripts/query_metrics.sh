#!/usr/bin/env bash
# Runs a PromQL instant query against the local Prometheus and prints ONLY
# the raw numeric result (no JSON, no labels) so it's trivially scriptable.
# Usage: scripts/query_metrics.sh '<promql>'
set -euo pipefail

query="${1:?usage: query_metrics.sh '<promql>'}"
prom_url="http://localhost:${PROMETHEUS_PORT:-9090}"

curl -sG --data-urlencode "query=${query}" "${prom_url}/api/v1/query" | python3 -c '
import json
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    print("could not parse Prometheus response -- is it running?", file=sys.stderr)
    sys.exit(1)

if payload["status"] != "success":
    print(payload.get("error", "unknown Prometheus error"), file=sys.stderr)
    sys.exit(1)

data = payload["data"]
result_type = data["resultType"]

if result_type == "scalar":
    print(data["result"][1])
elif result_type == "vector":
    result = data["result"]
    if not result:
        print("no data for query", file=sys.stderr)
        sys.exit(1)
    if len(result) > 1:
        labels = [r["metric"] for r in result]
        print(
            f"query returned {len(result)} series, expected 1 "
            f"-- aggregate with sum()/avg()/etc: {labels}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(result[0]["value"][1])
else:
    print(f"unsupported resultType {result_type!r} for an instant query", file=sys.stderr)
    sys.exit(1)
'
