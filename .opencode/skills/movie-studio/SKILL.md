# AI Movie Studio (OpenCode skill)

End-to-end workflow for **long-form AI-assembled video**: continuity JSON → scene/shot JSON → `studio` render → automatic visual QC rerenders → ffmpeg assemble (final file uses video and embedded audio from each clip).

## Setup Rules

- Chat/model settings live in OpenCode; video provider keys live in `.env`.
- Director edits only `continuity_bible.json` and `scenes.json` (OpenCode permissions). Change `providers/*.json` in the editor if you use the HTTP video driver.
- Subagents return JSON only; the director merges their output and validates.
- User scope is authoritative. Do not shrink requested runtime, scene count, shot count, genre, or deliverable to save cost or time unless the user explicitly approves.
- If the user says "continue", proceed with the next concrete pipeline step; do not stop to offer options when the next step is clear.
- Cost/provider warnings are status information, not permission to downscope. With `VIDEO_PROVIDER=custom` or `mock`, still preserve the full requested `scenes.json`; that mode only changes render quality.

## Workflow

1. **Brief** — Genre, tone, target length, aspect ratio / fps (`16:9` / `24` by default).
2. **Runtime math** — Convert runtime into shots when needed: `shots = ceil(minutes * 60 / shot_duration_sec)`. A true 90-minute feature at 10 seconds per shot is 540 shots.
3. **Continuity bible** — Edit `continuity_bible.json`; every character in `characters[]` must include a `profile` with locked visual/personality details (`physical_signature`, `face`, `hair`, `eyes`, `body`, `movement`, `personality`, `voice`, `consistency_notes`, `negative_prompt`, and a stable `seed` when possible). Add optional `video_style` for the **whole film** (not a few clips): use `aesthetic` for the master rendering bucket (photoreal vs anime vs documentary, etc.), plus look, camera, lighting, texture, grading, pacing; merged into **every** shot render automatically.
4. **Scenes** — Edit `scenes.json` with `"version": 1`; for large features, generate the full requested structure in batches or with a script, then validate.
5. **Plan** — `python -m studio plan` until OK.
6. **Provider check** — Run `python -m studio provider` before choosing the render path.
7. **Character consistency** — render commands inject matching `CharacterProfile` blocks for characters mentioned in each shot. Keep shot prompts focused and non-conflicting.
8. **Custom preview path** — If the provider resolves to `custom` or `mock`, skip automatic visual QC and use `python -m studio render-all` as a full-length pipeline validation run.
9. **Auto-QC path (default for generative providers)** — Render one shot at a time with `python -m studio render --scene ... --shot ...`, then build a visual proof sheet with `python -m studio review-sheet --scene ... --shot ... --attempt ...` (writes `dist/review/<scene>__<shot>__attempt_<NN>.png`), then send the clip path, review-sheet path, current prompt, duration, provider mode, and attempt number to `@quality-control`.
10. **Automatic rerender rules** — If Quality Control returns `rerender`, update `scenes.json` with the full replacement prompt and/or `duration_sec`, run `python -m studio plan`, and rerender that shot. Stop after 3 total attempts, repeated `issue_signature`, no material prompt/duration change, or confidence too low to justify another automatic retry.
11. **Assemble** — `python -m studio assemble -o dist/final.mp4` (concat clips; audio comes from each clip’s muxed stream).

## Definition of done

- `python -m studio plan` exits successfully (bible + scenes valid).
- Intended `VIDEO_PROVIDER` and keys in `.env` (unless intentionally `custom` or `mock` for layout tests).
- Each rendered shot either passed automatic QC, was intentionally skipped because the provider is `custom` or `mock`, or was reported unresolved after the retry guardrails fired.
- `assemble` writes `dist/final.mp4` (or chosen `-o` path).

