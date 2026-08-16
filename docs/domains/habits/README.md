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

## Habit completion (check-in)
A habit can have multiple daily completions. Each completion is recorded
for a specific date and represents one successful check-in for that habit.

- Completion date defaults to today if not provided
- Cannot record a completion for a future date (returns HTTP 422)
- Cannot record duplicate completions for the same habit and date (returns HTTP 409)

## Completions API
Endpoint: `POST /habits/{habit_id}/completions`

**Request body:**
- `completion_date` (optional, date string): Defaults to today if omitted

**Response:**
- HTTP 201 on success
- HTTP 404 if the habit doesn't exist
- HTTP 422 if completion date is in the future
- HTTP 409 if duplicate completion exists for this habit/date

**Error responses:**
- "Habit not found" (404)
- "Completion date cannot be in the future" (422)
- "Completion already recorded for this habit and date" (409)

## Related tickets
- "Create a habit (name, daily target, category)" — GitHub Issue #1
