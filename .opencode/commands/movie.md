---
description: Full movie pipeline from a brief (delegate to subagents, validate, render, assemble)
agent: director
---

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

**Steps you should cover:**

1. Summarize constraints (length, tone, aspect ratio).
2. Delegate only when useful:
   - use **@screenwriter** for scene `summary` / `dialogue` text,
   - use **@shotboard** for shot prompts / durations,
   - use **@quality-control** only after clips exist or the user asks for review.
3. When delegating, request the subagent's required output format and merge the result into JSON yourself.
4. Keep `continuity_bible.json` and `scenes.json` schema-valid; run `python -m studio plan` after edits.
5. Remind the user: **mock** video = test-pattern placeholders; **real** video needs `VIDEO_PROVIDER` + keys in `.env`.
6. When ready: `python -m studio render-all` then `python -m studio assemble -o dist/final.mp4`.
7. Offer **@quality-control** (Quality Control) review of output or a checklist if they share playback notes.

Always work from the repository root that contains `pyproject.toml`.