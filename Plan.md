# Plan: Add version field to /health endpoint response

## Context

Implement Issue #XX ("Add a version field to the /health endpoint response") as an end-to-end feature request. This requires modifying the health endpoint response to include a hardcoded "version": "0.1.0" field while preserving the existing "status": "ok" field.

## What this branch changes

**`app/main.py`** — modify the `/health` endpoint response to include a hardcoded version field "0.1.0".

**`tests/`** — update integration tests that verify the health endpoint to check for the new version field. This repurposes the pre-existing `test_create_habit_returns_201_and_persists` into the new health/version test, extracting its former body into a `_create_habit()` helper (still asserting everything it did before) so the habit-creation coverage isn't lost -- not a coverage reduction, just a rename plus extraction.

## Out of scope

- Real semantic versioning / version bumping automation

## Verification

- The /health endpoint now returns {"status": "ok", "version": "0.1.0"}
- Integration tests verify the version field is present and correct