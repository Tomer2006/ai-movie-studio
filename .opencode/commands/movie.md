---

## description: Full movie pipeline from a brief with automatic visual QC and rerenders

agent: director

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

Summarize constraints, preserve the requested runtime/scene/shot count, keep JSON schema-valid, validate with `python -m studio plan`, check provider, render/QC according to the skill, assemble, and report kept/rerendered/unresolved shots. Do not replace a requested feature-length plan with a shorter cost-saving version unless the user explicitly asks.