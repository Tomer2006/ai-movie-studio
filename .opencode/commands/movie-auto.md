---

## description: Full movie pipeline from a brief with forced automatic visual QC and rerenders

agent: director

Follow `.opencode/skills/movie-studio/SKILL.md` end-to-end.

**Film brief from the user:**

$ARGUMENTS

**Mode requirement:**

Automatic visual QC is required whenever the provider is not a custom ffmpeg preview (`custom` / `mock`). Summarize constraints, preserve the requested runtime/scene/shot count, validate JSON, check provider, render/QC according to the skill, assemble, and report kept/rerendered/unresolved shots. Do not replace a requested feature-length plan with a shorter cost-saving version unless the user explicitly asks.