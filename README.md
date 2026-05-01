# AI Movie Studio

Orchestration CLI for **long-form AI video**: validate continuity/scene JSON, render shots via cloud APIs (or a **custom** ffmpeg local preview), assemble with **ffmpeg** (concatenates clips; each clip contributes its own video and embedded audio).

**New to the OpenCode agent?** Read **[tutorial.md](tutorial.md)**.

## Setup

```powershell
cd ai-movie-studio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
# Edit .env — video: OPENROUTER_API_KEY + VIDEO_PROVIDER=openrouter, FAL_KEY + VIDEO_PROVIDER=fal, REPLICATE_API_TOKEN + VIDEO_PROVIDER=replicate, XAI_API_KEY + VIDEO_PROVIDER=xai, or custom (local preview)
```

Requires **ffmpeg** on your PATH for assembly and custom preview clips.

## Project files


| File                    | Role                                                               |
| ----------------------- | ------------------------------------------------------------------ |
| `continuity_bible.json` | Characters, locations, visual rules (validated against `schemas/`) |
| `scenes.json`           | Scene/shot list with prompts and durations                         |
| `clips/`                | Rendered per-shot MP4s                                             |
| `dist/`                 | Final output                                                       |


Copy examples: `continuity_bible.example.json` → `continuity_bible.json`, `scenes.example.json` → `scenes.json`.

## Character Consistency

Each `continuity_bible.json` character can include a `profile` with locked traits such as face, body, movement, voice, negative prompt, reference image, and seed. Render commands append only the `CharacterProfile` blocks for characters mentioned in each shot prompt.

## CLI

```text
studio plan --bible continuity_bible.json --scenes scenes.json
studio provider
studio render --scene scene_01 --shot s01_sh01
studio render-all
studio assemble --output dist/final.mp4
```

- `**plan**`: Validate JSON files against schemas and write resolved per-shot prompt sidecars to `clips/*.prompt.txt`.
- `**provider**`: Show the resolved video provider from `.env`.
- `**render` / `render-all**`: Generate clips — built-ins `openrouter`, `fal`, `replicate`, `xai`, `custom` (ffmpeg preview; `mock` is an alias), or **any HTTP API** via JSON (`[providers/README.md](providers/README.md)`, `VIDEO_PROVIDER=http` + `STUDIO_PROVIDER_CONFIG`).
- `**validate-provider`**: Check a provider JSON file against the schema.
- `**assemble`**: Concat clips in scene order with stream copy (video + embedded audio from each shot).

## Format presets

Set in `continuity_bible.json`:


| Field          | Typical values                               |
| -------------- | -------------------------------------------- |
| `aspect_ratio` | `16:9` (landscape), `9:16` (vertical), `1:1` |
| `fps`          | `24` (cinematic), `30`                       |


Shot `duration_sec` is per cloud model limits (often keep 5–15s per shot unless your provider supports longer via `REPLICATE_EXTRA_INPUT`).

## OpenCode

Open this repo root in a terminal and run `opencode`. `[opencode.json](opencode.json)` and `[opencode.jsonc](opencode.jsonc)` merge: `**opencode.jsonc`** holds all **agent** settings (including disabling **Plan** / **Build**, hiding **general** / **explore**, `default_agent`, subagent knobs). Switch to the **director** agent (Tab), then run `**/movie`** with your brief.

- **Director** — owns `continuity_bible.json`, `scenes.json`, and running `python -m studio …`.
- **Subagents** — `@screenwriter` (dialogue/summaries), `@shotboard` (shot prompts/durations), `@quality-control` (Quality Control / post-render fixes). Prompts: `[.opencode/agents/](.opencode/agents/)`; JSON agent config: `**[opencode.jsonc](opencode.jsonc)`**.
- Full workflow and Quality Control loop: `[.opencode/skills/movie-studio/SKILL.md](.opencode/skills/movie-studio/SKILL.md)`.

Chat LLM provider (OpenRouter, etc.) is configured in **OpenCode** (`/connect`, `/models`), not in `.env`. **Video** providers, including `VIDEO_PROVIDER=openrouter`, stay in `.env`.

## Pilot (local smoke test)

PowerShell from repo root (requires Python + ffmpeg):

```powershell
.\scripts\pilot.ps1
```

This uses `VIDEO_PROVIDER=custom` to validate the pipeline without cloud video APIs.