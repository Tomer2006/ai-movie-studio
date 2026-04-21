# Tutorial: Using the AI Movie Studio agent (OpenCode)

This guide is for people who want to **drive the pipeline through OpenCode** (the **director** agent and friends), not only the raw terminal commands.

---

## What you are running


| Piece            | Role                                                                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **OpenCode**     | The chat app where you talk to the **director** agent. It plans, edits JSON, and runs allowed shell commands.                                    |
| **LLM**          | Chosen inside OpenCode (`/connect`, `/models`, or `opencode.json`). Used for reasoning and writing text. **Not** the same as your video API key. |
| `**studio` CLI** | Python package in this repo: validates JSON, calls video APIs, runs **ffmpeg**. Reads `**.env`** for video keys.                                 |


You can use **only the CLI** without OpenCode; the agent is optional but helps with structure and pacing.

---

## Before you start

1. **Clone or open this folder** in Cursor (or any editor): the path that contains `pyproject.toml`.
2. **Python 3.11+** and **ffmpeg** on your PATH.
3. **Install the CLI** (PowerShell):
  ```powershell
   cd C:\Users\tomer\ai-movie-studio
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .
  ```
4. **Copy environment template**:
  ```powershell
   copy .env.example .env
  ```
5. **Install OpenCode** (if you have not): see [opencode.ai](https://opencode.ai/) or your package manager. You need the `opencode` command in a terminal.

---

## Keys: two different places


| What                                                             | Where                                                                                                                                                                                                      |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Video** (Replicate, xAI, or custom HTTP)                       | `**.env`** in this project: `VIDEO_PROVIDER`, `REPLICATE_API_TOKEN` or `XAI_API_KEY`, etc.                                                                                                                 |
| **Chat / planning LLM** (OpenRouter, Anthropic, OpenCode Zen, …) | **OpenCode**: run `**/connect`** or `**/models`**, or edit your global `opencode.json` under your user config. **Do not** put the chat LLM key in `.env` — it belongs in OpenCode / your provider tooling. |


---

## Configure video generation (`.env`)

Edit `.env` in the project root.

- **Real cloud video (xAI example):**
  ```env
  VIDEO_PROVIDER=xai
  XAI_API_KEY=your_key_here
  ```
- **Real cloud video (Replicate example):**
  ```env
  VIDEO_PROVIDER=replicate
  REPLICATE_API_TOKEN=your_token_here
  ```
- **Cheap local test (no AI footage):**
  ```env
  VIDEO_PROVIDER=mock
  ```
  Mock output looks like **color bars** and may show **MOCK** on screen. That is intentional; it checks your pipeline without spending API credits.
- **Custom HTTP provider:** see `[providers/README.md](providers/README.md)` and set `VIDEO_PROVIDER=custom` plus `STUDIO_PROVIDER_CONFIG=...`.

---

## Start OpenCode on this project

1. Open a terminal.
2. Go to the repo root (same folder as `pyproject.toml`):
  ```powershell
   cd C:\Users\tomer\ai-movie-studio
  ```
3. Run:
  ```text
   opencode
  ```
4. If `opencode` is not found, open a **new** terminal after install, or use the full path from your install location.

---

## Choose the **director** agent

This project’s `**[opencode.jsonc](opencode.jsonc)`** (merged with `[opencode.json](opencode.json)`) **disables** OpenCode’s built-in **Plan** and **Build** agents and **hides** the **general** and **explore** subagents from the `@` menu so the movie workflow stays focused. Use **director** as your main agent.

- Press **Tab** (or your configured key) until the active agent is **director**.
- The director is tuned for this repo: continuity bible, `scenes.json`, and running `python -m studio …`.

---

## Run the `**/movie`** command

Type:

```text
/movie Your film idea here — genre, length, tone, anything important.
```

Example:

```text
/movie A 5-minute quiet sci-fi short: a repair drone wakes up alone on a derelict station. Hopeful ending.
```

OpenCode loads the workflow from `[.opencode/skills/movie-studio/SKILL.md](.opencode/skills/movie-studio/SKILL.md)`. The director should:

1. Align `**continuity_bible.json**` and `**scenes.json**` with your brief.
2. Run `**python -m studio plan**` until validation passes.
3. Run `**python -m studio render-all**` when `.env` is set for the provider you want.
4. Run `**python -m studio assemble -o dist/final.mp4**` to build the final file.

If the venv is activated, `python -m studio` is enough; otherwise use the full path to `python` inside `.venv`.

---

## Subagents (optional)

You can **mention** these in chat; the director can also invoke them via the Task tool where allowed:


| Mention              | Use when                                                                        |
| -------------------- | ------------------------------------------------------------------------------- |
| **@screenwriter**    | Dialogue and scene summaries (text only; director pastes into JSON).            |
| **@shotboard**       | Shot-level prompts and durations (drafts for `scenes.json`).                    |
| **@quality-control** | Quality Control — after a render: what looks wrong, which shot ids to rerender. |


Subagents **do not edit files**; they reply in chat.

---

## What the director is allowed to do (permissions)

Configured in `[opencode.jsonc](opencode.jsonc)` (agent permissions and `default_agent`; merges with `[opencode.json](opencode.json)`):

- **Edit only:** `continuity_bible.json`, `scenes.json`, and `providers/*.json`.
- **Shell:** only `python -m studio …` / `py -m studio …` style commands are **allowed**. Other commands are **denied** (no approval dialogs).
- **Task:** can call **screenwriter**, **shotboard**, and **quality-control** only.

So the agent cannot silently change Python source, schemas, `.env`, or random files.

---

## Manual path (without `/movie`)

From the repo root, after `pip install -e .` and `.env` configured:

```powershell
python -m studio init-examples
python -m studio plan
python -m studio provider
python -m studio render-all
python -m studio assemble -o dist\final.mp4
```

Watch `**dist\final.mp4**`. To fix one shot:

```powershell
python -m studio render --scene scene_01 --shot s01_sh01
python -m studio assemble -o dist\final.mp4
```

---

## Troubleshooting


| Symptom                      | Likely cause                                                                                                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Color bars / “MOCK” on video | Usually `VIDEO_PROVIDER=mock`. Run `python -m studio provider` to confirm what the CLI resolved, then set `xai` or `replicate` (or custom) **and** the matching key in `.env` if needed. |
| `studio` not found           | Use `python -m studio` from the repo root, or activate `.venv` and reinstall `pip install -e .`.                                        |
| Validation errors            | Run `python -m studio plan` and match `[schemas/](schemas/)` and `[*.example.json](continuity_bible.example.json)`.                     |
| No audio in final file       | `assemble` copies streams from each clip; ensure your **video provider** or source clips include the audio you want muxed in each shot. |


---

## Where to read more

- [README.md](README.md) — CLI overview and OpenCode pointer.
- [.opencode/skills/movie-studio/SKILL.md](.opencode/skills/movie-studio/SKILL.md) — full workflow, Quality Control loop, definition of done.
- [providers/README.md](providers/README.md) — custom HTTP video providers.
- [OpenCode docs](https://opencode.ai/docs/) — providers, permissions, agents.

