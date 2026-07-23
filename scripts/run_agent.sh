#!/usr/bin/env bash
# Shared provider dispatch for every unattended-agent call site (the five
# .github/workflows/*.yml jobs, plus agent_review_local.sh/agent_review_cloud.sh).
# Every call site pipes a prompt into this script on stdin instead of calling
# `claude -p` directly, so AGENT_PROVIDER picks the backend in exactly one
# place. See issue #15 and docs/architecture/agent-providers.md.
#
# AGENT_PROVIDER=claude (default) -- claude -p, with the same flags/values
#   every call site passed before this script existed (flag order can
#   differ for the two review scripts' --tools/--system-prompt, since
#   they're now appended conditionally rather than written inline).
# AGENT_PROVIDER=north            -- Cohere's open-source North Mini Code,
#   run through the OpenCode CLI against OpenRouter. UNVERIFIED end-to-end --
#   see docs/architecture/agent-providers.md before pointing any auto-merge-
#   eligible workflow (doc-gardener.yml, garbage-collector.yml) at this.
#
# Usage: scripts/run_agent.sh [--tools <spec>] [--system-prompt <text>] <<< "$prompt"
#   --tools ""              no tool access at all (agent_review_local.sh)
#   --tools "Read,Glob,Grep" read-only tool access (agent_review_cloud.sh)
#   (omitted)                unrestricted tool access (the five workflows)
set -euo pipefail

PROVIDER="${AGENT_PROVIDER:-claude}"
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-5}"
NORTH_MODEL="${NORTH_MODEL:-cohere/north-mini-code:free}"

tools_given=0
tools=""
system_prompt=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tools)
            tools_given=1
            tools="$2"
            shift 2
            ;;
        --system-prompt)
            system_prompt="$2"
            shift 2
            ;;
        *)
            echo "run_agent.sh: unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

prompt="$(cat)"

run_claude() {
    if ! command -v claude >/dev/null 2>&1; then
        npm install -g @anthropic-ai/claude-code >&2
    fi

    local args=(-p --model "$CLAUDE_MODEL" --permission-mode bypassPermissions)
    [[ "$tools_given" -eq 1 ]] && args+=(--tools "$tools")
    [[ -n "$system_prompt" ]] && args+=(--system-prompt "$system_prompt")

    claude "${args[@]}" <<< "$prompt"
}

# OpenCode's `run` subcommand has no --tools-style flag of its own (confirmed
# against its docs while researching #15) -- tool access is only
# configurable via an agent definition's `permission`/`tools` block, so this
# generates a minimal one on the fly and points OPENCODE_CONFIG at it. Only
# the three tool specs actually used across every call site today are
# handled; anything else is a deliberate hard failure rather than a silent,
# wrong permission set.
run_north() {
    if ! command -v opencode >/dev/null 2>&1; then
        npm install -g opencode-ai >&2
    fi
    : "${OPENROUTER_API_KEY:?run_agent.sh: OPENROUTER_API_KEY must be set for AGENT_PROVIDER=north}"

    # OpenCode has no CLI flag for a one-off system prompt either -- fold it
    # into the message instead of the (unconfirmed) agent-config prompt field.
    if [[ -n "$system_prompt" ]]; then
        prompt="$system_prompt

$prompt"
    fi

    local config_file=""
    if [[ "$tools_given" -eq 1 ]]; then
        config_file="$(mktemp)"
        trap 'rm -f "$config_file"' RETURN

        local tools_json
        case "$tools" in
            "")
                tools_json='{"read":false,"glob":false,"grep":false,"list":false,"patch":false}'
                ;;
            "Read,Glob,Grep")
                tools_json='{"read":true,"glob":true,"grep":true,"list":true,"patch":false}'
                ;;
            *)
                echo "run_agent.sh: AGENT_PROVIDER=north has no mapping for --tools '$tools' -- add one in run_north() before using it." >&2
                exit 1
                ;;
        esac

        cat > "$config_file" <<CONFIG
{
  "agent": {
    "run-agent": {
      "mode": "primary",
      "permission": {"edit": "deny", "write": "deny", "bash": "deny", "webfetch": "deny"},
      "tools": $tools_json
    }
  }
}
CONFIG
        export OPENCODE_CONFIG="$config_file"
    fi

    local args=(run --model "openrouter/$NORTH_MODEL")
    [[ "$tools_given" -eq 1 ]] && args+=(--agent run-agent)

    # Undocumented whether `opencode run` reads a prompt from stdin -- its
    # docs only show a positional argument, which risks ARG_MAX on the
    # largest prompts here (full diffs, concatenated docs/ trees). Passing
    # positionally to match documented behavior; if that turns out to
    # truncate large prompts in practice, that's exactly the kind of gap the
    # real end-to-end run in docs/architecture/agent-providers.md needs to
    # catch before this provider is trusted anywhere.
    opencode "${args[@]}" "$prompt"
}

case "$PROVIDER" in
    claude) run_claude ;;
    north) run_north ;;
    *)
        echo "run_agent.sh: unknown AGENT_PROVIDER '$PROVIDER' (expected 'claude' or 'north')" >&2
        exit 1
        ;;
esac
