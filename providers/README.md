# Custom video providers (HTTP)

Any provider that exposes **JSON over HTTP** can be integrated without Python code by adding a config file validated against [`schemas/http_provider.schema.json`](../schemas/http_provider.schema.json).

## Enable

1. Copy [`http.example.json`](http.example.json) (async + poll) or [`http.immediate.example.json`](http.immediate.example.json) (sync URL in first response) to e.g. `providers/my_api.json` and edit it.
2. Put secrets in `.env` and reference them as `${ENV_NAME}` in the JSON (headers, URLs).
3. Either:
   - Set `VIDEO_PROVIDER=custom` and `STUDIO_PROVIDER_CONFIG=providers/my_api.json`, or
   - Set `VIDEO_PROVIDER=file:providers/my_api.json` (or `config:...`).

Validate before rendering:

```text
studio validate-provider providers/my_api.json
```

## Placeholders

| Placeholder | Meaning |
|-------------|---------|
| `{prompt}` | Shot prompt |
| `{duration_sec}` | Duration as string (float ok) |
| `{duration_int}` | Rounded integer (clamped 1–120 for the template) |
| `{aspect_ratio}` | From continuity bible, e.g. `16:9` |
| `{negative_prompt}` | Empty string if omitted |
| `{reference_image_url}` | Empty string if omitted |
| `{seed}` | Empty string if omitted |
| `{request_id}` | Only in `poll.url_template` / poll `body` after start |

Environment: `${MY_KEY}` is replaced from the process environment (`.env` loaded by the CLI).

## Modes

### `immediate`

The start response already contains the final video URL. Set `job.mode` to `immediate` and `job.video_url.path` to the JSON path to that URL.

### `poll`

1. Start request returns a job id — configure `job.request_id.path` (array of object keys).
2. Poll `job.poll.url_template` (include `{request_id}`) until `job.status.path` matches a value in `done_values` or `failed_values`.
3. Read the video URL with `job.video_url.path` from the **last poll response** when status is done.

## Download

Optional `download` block: if the video URL needs extra headers (rare), set `download.headers`.

## Built-in providers

For common APIs, the repo still ships **mock**, **replicate**, and **xai** — no JSON file required.

## Limits

The generic driver covers **REST JSON** with optional polling. It does **not** replace custom code for gRPC-only services, WebSocket-only progress, or multi-step OAuth device flows — use a small Python provider class for those.
