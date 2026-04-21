---

## description: Full movie pipeline from a brief with forced automatic visual QC and rerenders

agent: director

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

**Mode requirement:**

- Automatic visual QC is **required** for this run whenever the provider is not mock.
- Do not fall back to a manual review flow unless the provider resolves to `mock` or the user explicitly disables auto-rerenders.

**Steps you should cover:**

1. Summarize constraints (length, tone, aspect ratio).
2. Delegate only when useful:
  - use **@screenwriter** for scene `summary` / `dialogue` text,
  - use **@shotboard** for shot prompts / durations,
  - use **@quality-control** after each rendered shot as the automatic visual judge.
3. Keep `continuity_bible.json` and `scenes.json` schema-valid; run `python -m studio plan` after edits, including QC-driven prompt or duration changes.
4. Run `python -m studio provider` before rendering. If it resolves to `mock`, explain that automatic visual QC is skipped and use `python -m studio render-all` only as a pipeline check.
5. For non-mock providers, render shot-by-shot: `python -m studio render --scene ... --shot ...`, then `python -m studio review-sheet --scene ... --shot ... --attempt ...`, then call **@quality-control** and act on its JSON verdict automatically.
6. Retry a shot only when QC returns a material full replacement prompt or duration change, and never exceed 3 total attempts per shot.
7. Assemble at the end with `python -m studio assemble -o dist/final.mp4`.
8. Finish with a short report of kept shots, rerendered shots, and unresolved shots.

Always work from the repository root that contains `pyproject.toml`.