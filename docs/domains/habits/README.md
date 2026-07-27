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
- Cannot record a completion for a future date
- Cannot record duplicate completions for the same habit and date

## Related tickets
- "Create a habit (name, daily target, category)" — GitHub Issue #1
