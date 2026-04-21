---

## description: Full movie pipeline from a brief with automatic visual QC and rerenders

agent: director

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

**Steps you should cover:**

1. Summarize constraints (length, tone, aspect ratio).
2. Delegate only when useful:
  - use **@screenwriter** for scene `summary` / `dialogue` text,
  - use **@shotboard** for shot prompts / durations,
  - use **@quality-control** after each rendered shot when automatic QC is active.
3. When delegating, request the subagent's required output format and merge the result into JSON yourself.
4. Keep `continuity_bible.json` and `scenes.json` schema-valid; run `python -m studio plan` after edits, including any QC-driven prompt or duration changes.
5. Run `python -m studio provider` before rendering. If it resolves to `mock`, skip automatic QC and use `python -m studio render-all`.
6. For non-mock providers, render shot-by-shot: `python -m studio render --scene ... --shot ...`, then `python -m studio review-sheet --scene ... --shot ... --attempt ...`, then call **@quality-control** and act on its JSON verdict automatically.
7. Retry a shot only when QC returns a material full replacement prompt or duration change, and never exceed 3 total attempts per shot.
8. Assemble at the end with `python -m studio assemble -o dist/final.mp4`.
9. Finish with a short report of kept shots, rerendered shots, and unresolved shots.

Always work from the repository root that contains `pyproject.toml`.