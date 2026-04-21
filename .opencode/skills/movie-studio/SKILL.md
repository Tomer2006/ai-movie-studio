# AI Movie Studio (OpenCode skill)

End-to-end workflow for **long-form AI-assembled video**: continuity JSON → scene/shot JSON → `studio` render → ffmpeg assemble → optional TTS.

## Model choice (OpenCode vs video API)

- **OpenCode LLM** (chat / director): choose in OpenCode (`/models`, `opencode.json`, or `/connect` e.g. OpenRouter). Use models with strong **instruction-following** and **JSON** discipline for bible/scenes edits.
- **Video** API keys live only in `**.env`** (`VIDEO_PROVIDER`, `XAI_API_KEY`, `REPLICATE_API_TOKEN`, etc.) — not in `opencode.json`. The `studio` CLI reads `.env` for *render*, not the IDE’s LLM.

## Prerequisites

- Python 3.11+, `ffmpeg` on PATH
- From repo root: `pip install -e .` (venv recommended)
- `.env` from `.env.example` — set video provider + keys for real footage

## Roles (delegation)


| Role          | Who           | Focus                                                                                                                                                                                             |
| ------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Director      | Primary agent | May **edit only** `continuity_bible.json`, `scenes.json`, `providers/*.json`. May run `**python -m studio …*`* / `**py -m studio …**` only; other shell commands are **denied** (no approval UI). |
| @screenwriter | Subagent      | Dialogue + narration + summaries — **cannot edit files** (output in chat for director to paste)                                                                                                   |
| @shotboard    | Subagent      | Shot `prompt` + `duration_sec` drafts — **cannot edit files**                                                                                                                                     |
| @quality-control | Subagent   | Quality Control — post-render review — **cannot edit files**                                                                                                                                     |


Permissions live in `[opencode.json](../../opencode.json)` (OpenCode merges with agent markdown).

## One-shot command block (repo root)

PowerShell (replace nothing if you use venv at `.venv`):

```powershell
cd C:\Users\tomer\ai-movie-studio
.\.venv\Scripts\Activate.ps1
python -m studio plan
python -m studio render-all
python -m studio assemble -o dist\final.mp4
```

Validate a custom HTTP provider file:

```powershell
python -m studio validate-provider providers\my_provider.json
```

## Workflow

1. **Brief** — Genre, tone, target length, aspect ratio / fps (`16:9` / `24` by default).
2. **Continuity bible** — Edit `continuity_bible.json` (see `continuity_bible.example.json` + `schemas/`).
3. **Scenes** — Edit `scenes.json` with `"version": 1`.
4. **Plan** — `python -m studio plan` until OK.
5. **Render** — `python -m studio render-all`. **Mock** output intentionally looks like test bars + “MOCK” overlay — not a renderer bug. For real AI video set `VIDEO_PROVIDER=xai` or `replicate` (or `custom`) **and** API keys in `.env`.
6. **Assemble** — `python -m studio assemble -o dist/final.mp4` (narration from scene `narration` + `TTS_PROVIDER`).

## Human Quality Control loop (required for quality)

1. Watch `**dist/final.mp4`** (or individual clips under `clips/`).
2. For one bad take: tweak that shot’s `prompt` in `scenes.json`, then rerender **only** that shot:
  ```powershell
   python -m studio render --scene scene_01 --shot s01_sh01
  ```
3. Reassemble:
  ```powershell
   python -m studio assemble -o dist\final.mp4
  ```
4. Optionally invoke **@quality-control** (Quality Control) with notes (“faces drift on s01_sh02”) for a structured fix list.

Long projects: render **by scene** mentally (batch validation) to limit cost and failure blast radius.

## Definition of done

- `python -m studio plan` exits successfully (bible + scenes valid).
- Intended `VIDEO_PROVIDER` and keys in `.env` (unless intentionally mock for layout tests).
- `render-all` completes; clips exist under `clips/` with expected naming `scene_id__shot_id.mp4`.
- `assemble` writes `dist/final.mp4` (or chosen `-o` path).
- User has been told mock vs real video; Quality Control loop documented if they want polish.

## Format presets (continuity bible)


| Field          | Typical values        |
| -------------- | --------------------- |
| `aspect_ratio` | `16:9`, `9:16`, `1:1` |
| `fps`          | `24`, `30`            |


Provider-specific generation knobs: Replicate → `REPLICATE_EXTRA_INPUT`; custom HTTP → JSON in `[providers/README.md](../../providers/README.md)`.

## Command reference


| Command                                       | Purpose                         |
| --------------------------------------------- | ------------------------------- |
| `python -m studio init-examples`              | Seed example JSON files         |
| `python -m studio plan`                       | Validate bible + scenes schemas |
| `python -m studio validate-provider [file]`   | Validate HTTP provider JSON     |
| `python -m studio render-all`                 | All shots                       |
| `python -m studio render --scene X --shot Y`  | One shot                        |
| `python -m studio assemble -o dist/final.mp4` | Concat + TTS                    |


