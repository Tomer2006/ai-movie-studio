---
description: Full movie pipeline from a brief (delegate to subagents, validate, render, assemble)
agent: director
---

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

**Steps you should cover:**

1. Summarize constraints (length, tone, aspect ratio).  
2. Use **@screenwriter** for narration/dialogue/summaries and **@shotboard** for shot prompts/durations when it reduces errors; merge into JSON yourself.  
3. Keep `continuity_bible.json` and `scenes.json` schema-valid; run `python -m studio plan` after edits.  
4. Remind the user: **mock** video = test-pattern placeholders; **real** video needs `VIDEO_PROVIDER` + keys in `.env`.  
5. When ready: `python -m studio render-all` then `python -m studio assemble -o dist/final.mp4`.  
6. Offer **@qc** review of output or a QC checklist if they share playback notes.

Always work from the repository root that contains `pyproject.toml`.
