# Workflow

## Development Process
- Test-Driven Development (TDD) with Red-Green-Refactor cycle
- Coverage target: 80%
- Commit per task completion

## Branch Strategy
- Feature branches from main
- PR-based review before merge

## Track Structure
Each feature/bug track has:
- `spec.md` — requirements and acceptance criteria
- `plan.md` — phased implementation plan with TDD tasks
- `metadata.json` — track state and progress

## Implementation Order
1. Write failing test (Red)
2. Implement minimum code to pass (Green)
3. Refactor if needed
4. Commit
5. Move to next task
