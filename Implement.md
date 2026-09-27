# Implement.md - Documentation Freshness Fixes Implementation

This document describes the specific changes made to fix the documentation inconsistencies found in AGENTS.md.

## Changes Made

### 1. AGENTS.md Line 245 - Clarified "three scheduled workflows"

**Before:**
```
None of the three scheduled workflows above can use GitHub's native
gh pr merge --auto: that feature's "wait for required checks" behavior
only exists via branch protection, which 403s on this repo (issue #7). So
```

**After:**
```
None of the three workflows that never auto-merge (agent-ticket.yml, agent-followup.yml, quality-grader.yml) can use GitHub's native
gh pr merge --auto: that feature's "wait for required checks" behavior
only exists via branch protection, which 403s on this repo (issue #7). So
```

**Rationale:** The original text referred to "three scheduled workflows above" without clearly identifying which three workflows were being referenced. The updated text clearly specifies the three workflows that never auto-merge (agent-ticket.yml, agent-followup.yml, quality-grader.yml) and are therefore unable to use GitHub's native gh pr merge --auto feature.

### 2. AGENTS.md Line 285 - Clarified "three scheduled workflows"

**Before:**
```
GitHub auto-disables `schedule:`-triggered workflows after 60 days of no
repository activity (silently — an email, not a visible Actions-tab
failure). If one of the three scheduled workflows above appears to have
stopped running, check that first before assuming a bug in the workflow
itself.
```

**After:**
```
GitHub auto-disables `schedule:`-triggered workflows after 60 days of no
repository activity (silently — an email, not a visible Actions-tab
failure). If one of the scheduled workflows above appears to have
stopped running, check that first before assuming a bug in the workflow
itself.
```

**Rationale:** The original text referred to "three scheduled workflows above" without specifying which three workflows were being referenced. Since AGENTS.md lists 5 scheduled workflows (agent-ticket.yml, agent-followup.yml, doc-gardener.yml, garbage-collector.yml, quality-grader.yml), the term "three scheduled workflows" was ambiguous and potentially misleading. The updated text uses "one of the scheduled workflows" which is clearer and avoids the ambiguity.

## Summary

These changes improve the clarity and consistency of AGENTS.md by:

1. Removing ambiguous references to "three scheduled workflows"
2. Clearly specifying which workflows are being referenced in each context
3. Maintaining the accuracy of the information while improving readability

The changes are documentation-only and do not affect the actual functionality of the system.