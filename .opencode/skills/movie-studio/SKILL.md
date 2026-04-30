# AI Movie Studio (OpenCode skill)

End-to-end workflow for **long-form AI-assembled video**: continuity JSON → scene/shot JSON → `studio` render → automatic visual QC rerenders → ffmpeg assemble (final file uses video and embedded audio from each clip).

## Setup Rules

- Chat/model settings live in OpenCode; video provider keys live in `.env`.
- Director edits only `continuity_bible.json`, `scenes.json`, and `providers/*.json`.
- Subagents return JSON only; the director merges their output and validates.

## Workflow

1. **Brief** — Genre, tone, target length, aspect ratio / fps (`16:9` / `24` by default).
2. **Continuity bible** — Edit `continuity_bible.json`; put recurring character locks in `characters[].profile`.
3. **Scenes** — Edit `scenes.json` with `"version": 1`.
4. **Plan** — `python -m studio plan` until OK.
5. **Provider check** — Run `python -m studio provider` before choosing the render path.
6. **Character consistency** — render commands inject matching `CharacterProfile` blocks for characters mentioned in each shot. Keep shot prompts focused and non-conflicting.
7. **Mock path** — If the provider resolves to `mock`, skip automatic visual QC and use `python -m studio render-all` only as a cheap pipeline validation run.
8. **Auto-QC path (default for non-mock)** — Render one shot at a time with `python -m studio render --scene ... --shot ...`, then build a visual proof sheet with `python -m studio review-sheet --scene ... --shot ... --attempt ...`, then send the clip path, review-sheet path, current prompt, duration, provider mode, and attempt number to `@quality-control`.
9. **Automatic rerender rules** — If Quality Control returns `rerender`, update `scenes.json` with the full replacement prompt and/or `duration_sec`, run `python -m studio plan`, and rerender that shot. Stop after 3 total attempts, repeated `issue_signature`, no material prompt/duration change, or confidence too low to justify another automatic retry.
10. **Assemble** — `python -m studio assemble -o dist/final.mp4` (concat clips; audio comes from each clip’s muxed stream).

## Definition of done

- `python -m studio plan` exits successfully (bible + scenes valid).
- Intended `VIDEO_PROVIDER` and keys in `.env` (unless intentionally mock for layout tests).
- Each rendered shot either passed automatic QC, was intentionally skipped because the provider is mock, or was reported unresolved after the retry guardrails fired.
- `assemble` writes `dist/final.mp4` (or chosen `-o` path).