---

## description: Full movie pipeline from a brief with automatic visual QC and rerenders

agent: director

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

Summarize constraints, keep JSON schema-valid, validate with `python -m studio plan`, check provider, render/QC according to the skill, assemble, and report kept/rerendered/unresolved shots.