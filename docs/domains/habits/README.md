# Domain: Habits

## What a Habit is
A user-defined habit with a name, a daily target count, and a category/tag.
Habits are created once and tracked daily via check-ins (future domain).

## Fields
- name: string, 1-100 chars, required
- daily_target: integer, > 0, required
- category: string, 1-50 chars, required
- created_at: set server-side, not client-provided

## Out of scope (for now)
- Updating or deleting habits
- Listing all habits
- Daily check-ins / streak calculation (separate future domain)

## Related tickets
- "Create a habit (name, daily target, category)" — GitHub Issue #1
