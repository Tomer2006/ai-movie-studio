from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Optional

import typer

from studio.assemble import assemble as run_assemble
from studio.paths import load_dotenv, repo_root
from studio.providers import get_provider
from studio.providers.configurable import ConfigurableHttpProvider
from studio.providers.mock import MockVideoProvider
from studio.scenes_io import clip_path, iter_shots
from studio.validate import (
    load_and_validate_bible,
    load_and_validate_scenes,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _warn_if_mock(provider: object) -> None:
    if isinstance(provider, MockVideoProvider):
        msg = (
            "Using MOCK video (ffmpeg test pattern) - not AI-generated footage. "
            "Set VIDEO_PROVIDER=xai or replicate (+ API key in .env) for real video."
        )
        typer.echo(typer.style(msg, fg=typer.colors.YELLOW, bold=True))


@app.command("plan")
def plan_cmd(
    bible: Annotated[
        Optional[Path], typer.Option("--bible", help="continuity_bible.json path")
    ] = None,
    scenes: Annotated[Optional[Path], typer.Option("--scenes", help="scenes.json path")] = None,
) -> None:
    """Validate continuity bible and scenes against JSON Schema."""
    root = repo_root()
    bp = bible or (root / "continuity_bible.json")
    sp = scenes or (root / "scenes.json")
    load_and_validate_bible(bp)
    load_and_validate_scenes(sp)
    typer.echo(f"OK: {bp} and {sp} are valid.")


@app.command("render")
def render_cmd(
    scene: Annotated[str, typer.Option("--scene", help="Scene id")],
    shot: Annotated[str, typer.Option("--shot", help="Shot id")],
    bible: Annotated[Optional[Path], typer.Option("--bible")] = None,
    scenes: Annotated[Optional[Path], typer.Option("--scenes")] = None,
    clips_dir: Annotated[Optional[Path], typer.Option("--clips-dir")] = None,
) -> None:
    """Render a single shot to clips/."""
    load_dotenv()
    root = repo_root()
    bp = bible or (root / "continuity_bible.json")
    sp = scenes or (root / "scenes.json")
    bible_doc = load_and_validate_bible(bp)
    scenes_doc = load_and_validate_scenes(sp)
    cdir = clips_dir or (root / "clips")
    provider = get_provider()
    _warn_if_mock(provider)

    shot_data = None
    for sc in scenes_doc["scenes"]:
        if sc["id"] != scene:
            continue
        for sh in sc["shots"]:
            if sh["id"] == shot:
                shot_data = sh
                break
    if shot_data is None:
        raise typer.BadParameter(f"Shot not found: scene={scene!r} shot={shot!r}")

    out = clip_path(cdir, scene, shot)
    typer.echo(f"Rendering {out} ...")
    provider.render_shot(
        output_path=out,
        prompt=shot_data["prompt"],
        duration_sec=float(shot_data["duration_sec"]),
        negative_prompt=shot_data.get("negative_prompt"),
        aspect_ratio=bible_doc["aspect_ratio"],
        fps=int(bible_doc["fps"]),
        seed=shot_data.get("seed"),
        reference_image_url=shot_data.get("reference_image_url"),
    )
    typer.echo(f"Wrote {out}")


@app.command("render-all")
def render_all_cmd(
    bible: Annotated[Optional[Path], typer.Option("--bible")] = None,
    scenes: Annotated[Optional[Path], typer.Option("--scenes")] = None,
    clips_dir: Annotated[Optional[Path], typer.Option("--clips-dir")] = None,
) -> None:
    """Render every shot (ordered)."""
    load_dotenv()
    root = repo_root()
    bp = bible or (root / "continuity_bible.json")
    sp = scenes or (root / "scenes.json")
    bible_doc = load_and_validate_bible(bp)
    scenes_doc = load_and_validate_scenes(sp)
    cdir = clips_dir or (root / "clips")
    provider = get_provider()
    _warn_if_mock(provider)

    for ref in iter_shots(scenes_doc):
        out = clip_path(cdir, ref.scene_id, ref.shot_id)
        typer.echo(f"Rendering {ref.scene_id}/{ref.shot_id} -> {out}")
        provider.render_shot(
            output_path=out,
            prompt=ref.prompt,
            duration_sec=ref.duration_sec,
            negative_prompt=ref.negative_prompt,
            aspect_ratio=bible_doc["aspect_ratio"],
            fps=int(bible_doc["fps"]),
            seed=ref.seed,
            reference_image_url=ref.reference_image_url,
        )
    typer.echo("Done.")


@app.command("assemble")
def assemble_cmd(
    bible: Annotated[Optional[Path], typer.Option("--bible")] = None,
    scenes: Annotated[Optional[Path], typer.Option("--scenes")] = None,
    clips_dir: Annotated[Optional[Path], typer.Option("--clips-dir")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o")] = None,
) -> None:
    """Concatenate rendered clips (video + embedded audio from each clip)."""
    root = repo_root()
    sp = scenes or (root / "scenes.json")
    scenes_doc = load_and_validate_scenes(sp)
    cdir = clips_dir or (root / "clips")
    outp = output or (root / "dist" / "final.mp4")
    path = run_assemble(scenes_doc=scenes_doc, clips_dir=cdir, output_mp4=outp)
    typer.echo(f"Wrote {path}")


@app.command("validate-provider")
def validate_provider_cmd(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="JSON file (default: STUDIO_PROVIDER_CONFIG under repo root)"),
    ] = None,
) -> None:
    """Validate a configurable HTTP provider JSON schema."""
    load_dotenv()
    root = repo_root()
    if path is None:
        rel = os.environ.get("STUDIO_PROVIDER_CONFIG", "").strip()
        if not rel:
            raise typer.BadParameter("Pass a path or set STUDIO_PROVIDER_CONFIG in .env")
        path = root / rel
    p = path if path.is_absolute() else (root / path)
    ConfigurableHttpProvider.from_file(p)
    typer.echo(f"OK: {p}")


@app.command("init-examples")
def init_examples_cmd(
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
) -> None:
    """Copy *.example.json to project JSON files."""
    root = repo_root()
    targets = [
        (root / "continuity_bible.example.json", root / "continuity_bible.json"),
        (root / "scenes.example.json", root / "scenes.json"),
    ]
    for src, dst in targets:
        if dst.exists() and not force:
            typer.echo(f"Skip existing {dst} (use --force)")
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        typer.echo(f"Wrote {dst}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
