# Domain: Habits

## What a Habit is
A user-defined habit with a name, a daily target count, and a category/tag.
Habits can be created, listed, retrieved by ID, and tracked daily via check-ins.

## Available operations
- Create a habit
- List all habits
- Get a single habit by ID
- Record a habit completion (daily check-in)

## Fields
- name: string, 1-100 chars, required
- daily_target: integer, > 0, required
- category: string, 1-50 chars, required
- created_at: set server-side, not client-provided

## Completions API
Endpoint: `POST /habits/{habit_id}/completions`

**Request body:**
- `completion_date` (optional, date string): If omitted, defaults to today

**Response:**
- HTTP 201 on success
- HTTP 404 if the habit doesn't exist
- HTTP 422 if completion date is in the future
- HTTP 409 if duplicate completion exists for this habit/date

**Error responses:**
- "Habit not found" (404)
- "Completion date cannot be in the future" (422)
- "Completion already recorded for this habit and date" (409)

**Response model:** `CompletionRead` with fields: `id`, `habit_id`, `completion_date`, `created_at`

## Related tickets
- "Create a habit (name, daily target, category)" — GitHub Issue #1
