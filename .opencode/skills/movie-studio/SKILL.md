# AI Movie Studio (OpenCode skill)

End-to-end workflow for **long-form AI-assembled video**: continuity JSON → scene/shot JSON → `studio` render → automatic visual QC rerenders → ffmpeg assemble (final file uses video and embedded audio from each clip).

## Model choice (OpenCode vs video API)

- **OpenCode LLM** (chat / director): choose in OpenCode (`/models`, `opencode.json`, or `/connect` e.g. OpenRouter). Use models with strong **instruction-following** and **JSON** discipline for bible/scenes edits.
- **Video** API keys live only in `**.env`** (`VIDEO_PROVIDER`, `XAI_API_KEY`, `REPLICATE_API_TOKEN`, etc.) — not in `opencode.json`. The `studio` CLI reads `.env` for *render*, not the IDE’s LLM.

## Prerequisites

- Python 3.11+, `ffmpeg` on PATH
- From repo root: `pip install -e .` (venv recommended)
- `.env` from `.env.example` — set video provider + keys for real footage

## Roles (delegation)


| Role             | Who           | Focus                                                                                                                                                                                             |
| ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Director         | Primary agent | May **edit only** `continuity_bible.json`, `scenes.json`, `providers/*.json`. May run `**python -m studio …`** / `**py -m studio …`** only; other shell commands are **denied** (no approval UI). |
| @screenwriter    | Subagent      | Dialogue + scene summaries — **cannot edit files** (output in chat for director to paste)                                                                                                         |
| @shotboard       | Subagent      | Shot `prompt` + `duration_sec` drafts — **cannot edit files**                                                                                                                                     |
| @quality-control | Subagent      | Quality Control — machine-readable visual rerender verdicts — **cannot edit files**                                                                                                               |


Agent JSON (`default_agent`, optional `hidden` / `temperature`, permissions) lives in `[opencode.jsonc](../../opencode.jsonc)`. Project-wide permission defaults live in `[opencode.json](../../opencode.json)`. This repo sets **allow** / **deny** only (no `ask`) for the movie agents; merged rules follow OpenCode’s **last matching rule wins** (see [permissions](https://opencode.ai/docs/agents#permissions)). OpenCode merges these with agent markdown under `[.opencode/agents/](../../.opencode/agents/)`.

## Subagent output contracts

- **@screenwriter** — return **JSON only**:
  ```json
  [
    {
      "scene_id": "scene_01",
      "summary": "1-3 sentence scene summary.",
      "dialogue": "Optional spoken lines."
    }
  ]
  ```
- **@shotboard** — return **JSON only**:
  ```json
  [
    {
      "scene_id": "scene_01",
      "shots": [
        {
          "id": "s01_sh01",
          "duration_sec": 6,
          "prompt": "Single strong cinematic prompt."
        }
      ]
    }
  ]
  ```
- **@quality-control** — return **JSON only**:
  ```json
  {
    "decision": "<keep|rerender|unresolved>",
    "confidence": "<high|medium|low>",
    "issues": ["<short_issue_if_any>"],
    "issue_signature": "<acceptable_or_primary_issue>",
    "updated_prompt": null,
    "updated_duration_sec": null,
    "rationale": "Short explanation of the verdict."
  }
  ```
  Treat the placeholder values above as schema markers only, not defaults. Quality Control should choose `keep` only when the evidence clearly supports shipping the shot; if the evidence is ambiguous, prefer `unresolved`.

The **director** should merge subagent output into repo JSON itself and keep everything schema-valid.

## One-shot command block (repo root)

PowerShell (replace nothing if you use venv at `.venv`):

```powershell
cd C:\Users\tomer\ai-movie-studio
.\.venv\Scripts\Activate.ps1
python -m studio plan
python -m studio provider
python -m studio render --scene scene_01 --shot s01_sh01
python -m studio review-sheet --scene scene_01 --shot s01_sh01 --attempt 1
python -m studio assemble -o dist\final.mp4
```

Validate a custom HTTP provider file:

```powershell
python -m studio validate-provider providers\my_provider.json
```

## Workflow

1. **Brief** — Genre, tone, target length, aspect ratio / fps (`16:9` / `24` by default).
2. **Continuity bible** — Edit `continuity_bible.json` (see `continuity_bible.example.json` + `schemas/`). For recurring characters, fill the `profile` object with locked face, hair/eyes, body, wardrobe, movement, personality, voice, consistency notes, and negative prompt traits.
3. **Scenes** — Edit `scenes.json` with `"version": 1`.
4. **Plan** — `python -m studio plan` until OK.
5. **Provider check** — Run `python -m studio provider` before choosing the render path.
6. **Character consistency** — `studio render` and `studio render-all` automatically append `CharacterProfile` blocks from the continuity bible to every shot prompt. Keep shot prompts focused on camera/action/location and avoid contradicting the locked profile.
7. **Mock path** — If the provider resolves to `mock`, skip automatic visual QC and use `python -m studio render-all` only as a cheap pipeline validation run.
8. **Auto-QC path (default for non-mock)** — Render one shot at a time with `python -m studio render --scene ... --shot ...`, then build a visual proof sheet with `python -m studio review-sheet --scene ... --shot ... --attempt ...`, then send the clip path, review-sheet path, current prompt, duration, provider mode, and attempt number to `@quality-control`.
9. **Automatic rerender rules** — If Quality Control returns `rerender`, update `scenes.json` with the full replacement prompt and/or `duration_sec`, run `python -m studio plan`, and rerender that shot. Stop after 3 total attempts, repeated `issue_signature`, no material prompt/duration change, or confidence too low to justify another automatic retry.
10. **Assemble** — `python -m studio assemble -o dist/final.mp4` (concat clips; audio comes from each clip’s muxed stream).

## Automatic Quality Control loop (default)

1. Start with `python -m studio provider`.
2. If the provider is `mock`, skip visual QC and use `render-all`.
3. For a non-mock provider, for each shot attempt:
  ```powershell
  python -m studio render --scene scene_01 --shot s01_sh01
  python -m studio review-sheet --scene scene_01 --shot s01_sh01 --attempt 1
  ```
4. Ask `@quality-control` for a JSON verdict. If it returns `rerender`, patch `scenes.json`, re-run `python -m studio plan`, and retry the shot.
5. Reassemble when all shots are either kept or unresolved:
  ```powershell
  python -m studio assemble -o dist\final.mp4
  ```
6. End by reporting kept shots, rerendered shots, and unresolved shots.

## Manual fallback

If the automatic loop stops with unresolved shots, inspect `dist/review/...` and `clips/...` yourself, then refine prompts manually and rerun only those shots.

## Definition of done

- `python -m studio plan` exits successfully (bible + scenes valid).
- Intended `VIDEO_PROVIDER` and keys in `.env` (unless intentionally mock for layout tests).
- Each rendered shot either passed automatic QC, was intentionally skipped because the provider is mock, or was reported unresolved after the retry guardrails fired.
- Clips exist under `clips/` with expected naming `scene_id__shot_id.mp4`.
- `assemble` writes `dist/final.mp4` (or chosen `-o` path).
- User has been told how to verify mock vs real video with `python -m studio provider`; automatic QC guardrails are documented.

## Format presets (continuity bible)


| Field          | Typical values        |
| -------------- | --------------------- |
| `aspect_ratio` | `16:9`, `9:16`, `1:1` |
| `fps`          | `24`, `30`            |


Provider-specific generation knobs: Replicate → `REPLICATE_EXTRA_INPUT`; custom HTTP → JSON in `[providers/README.md](../../providers/README.md)`.

## Command reference


| Command                                                        | Purpose                         |
| -------------------------------------------------------------- | ------------------------------- |
| `python -m studio init-examples`                               | Seed example JSON files         |
| `python -m studio plan`                                        | Validate bible + scenes schemas |
| `python -m studio validate-provider [file]`                    | Validate HTTP provider JSON     |
| `python -m studio provider`                                    | Show resolved video provider    |
| `python -m studio render-all`                                  | All shots (no per-shot auto-QC) |
| `python -m studio render --scene X --shot Y`                   | One shot                        |
| `python -m studio review-sheet --scene X --shot Y --attempt N` | Build a shot review PNG         |
| `python -m studio assemble -o dist/final.mp4`                  | Concat clips (copy streams)     |


