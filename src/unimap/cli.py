"""CLI entry point for UniMap."""
from __future__ import annotations

import dataclasses
import json
import logging
import sys
from pathlib import Path

import click

from unimap.config import ANNOTATIONS_DIR, GEOJSON_DIR, IMAGES_DIR, SQLITE_DB, ensure_dirs


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """UniMap: text recognition on historical map scans."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    ensure_dirs()


@main.command()
@click.option("--stanford", default=20, help="Number of Stanford maps to harvest")
@click.option("--rumsey", default=20, help="Number of Rumsey maps to harvest")
@click.option("--output", "-o", default="data/records.json", help="Output records file")
def harvest(stanford: int, rumsey: int, output: str) -> None:
    """Step 1: Harvest map metadata from Stanford Earthworks and David Rumsey."""
    from unimap.harvest.rumsey import harvest as harvest_rumsey
    from unimap.harvest.stanford import harvest as harvest_stanford

    records = []
    click.echo(f"Harvesting {stanford} maps from Stanford Earthworks...")
    records.extend(harvest_stanford(limit=stanford))
    click.echo(f"Harvesting {rumsey} maps from David Rumsey...")
    records.extend(harvest_rumsey(limit=rumsey))

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([dataclasses.asdict(r) for r in records], f, indent=2)

    click.echo(f"Harvested {len(records)} map records -> {out_path}")


@main.command()
@click.option("--records", "-r", default="data/records.json", help="Records file from harvest")
@click.option("--max-width", default=4096, help="Max image width to download")
def download(records: str, max_width: int) -> None:
    """Step 2: Download map images via IIIF Image API."""
    from unimap.download.iiif import download_all
    from unimap.harvest.models import MapRecord

    with open(records) as f:
        data = json.load(f)
    map_records = [MapRecord(**r) for r in data]

    click.echo(f"Downloading {len(map_records)} map images (max width: {max_width}px)...")
    results = download_all(map_records, max_width=max_width)
    click.echo(f"Downloaded {len(results)} images")


@main.command()
@click.option("--records", "-r", default="data/records.json", help="Records file from harvest")
@click.option(
    "--spotter", default="paddle", type=click.Choice(["paddle", "spotter-v2"]),
    help="Text spotter backend",
)
@click.option("--patch-size", default=1000, help="Patch size in pixels")
@click.option("--overlap", default=200, help="Patch overlap in pixels")
def ocr(records: str, spotter: str, patch_size: int, overlap: int) -> None:
    """Step 3: Run text recognition on downloaded map images."""
    from unimap.harvest.models import MapRecord
    from unimap.ocr.patchify import run_ocr_on_map
    from unimap.output.annotation import write_annotations
    from unimap.output.geojson import write_geojson

    with open(records) as f:
        data = json.load(f)
    map_records = [MapRecord(**r) for r in data]

    if spotter == "paddle":
        from unimap.ocr.paddle_spotter import PaddleSpotter

        text_spotter = PaddleSpotter()
    elif spotter == "spotter-v2":
        from unimap.ocr.spotter_v2 import SpotterV2

        text_spotter = SpotterV2()
    else:
        raise click.BadParameter(f"Unknown spotter: {spotter}")

    text_spotter.warmup()

    for record in map_records:
        image_path = IMAGES_DIR / record.source / f"{record.slug}.jpg"
        if not image_path.exists():
            click.echo(f"SKIP {record.slug}: image not found at {image_path}", err=True)
            continue

        click.echo(f"OCR {record.slug}: {record.title}")
        result = run_ocr_on_map(
            record, image_path, text_spotter,
            patch_size=patch_size, overlap=overlap,
        )

        gj_path = write_geojson(record, result)
        anno_path = write_annotations(record, result)
        click.echo(
            f"  -> {len(result.detections)} detections"
            f" | {gj_path.name} | {anno_path.name}"
        )


@main.command()
def index() -> None:
    """Step 4: Build SQLite full-text search index from GeoJSON results."""
    from unimap.index.sqlite_index import index_all_geojson

    click.echo("Building search index...")
    total = index_all_geojson()
    click.echo(f"Indexed {total} text entries into {SQLITE_DB}")


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, help="Max results to return")
def search(query: str, limit: int) -> None:
    """Search for text across all indexed maps."""
    from unimap.index.sqlite_index import search as do_search

    results = do_search(query, limit=limit)

    if not results:
        click.echo(f"No results for '{query}'")
        return

    click.echo(f"Found {len(results)} results for '{query}':\n")
    for r in results:
        click.echo(f"  [{r['source']}] {r['title']}")
        click.echo(f"    Text: \"{r['text']}\" (confidence: {r['confidence']:.2f})")
        click.echo(
            f"    Canvas region: x={r['bbox_x']}, y={r['bbox_y']}, "
            f"w={r['bbox_w']}, h={r['bbox_h']}"
        )
        click.echo(f"    IIIF: {r['iiif_manifest']}")
        click.echo()


@main.command(name="run-all")
@click.option("--stanford", default=20, help="Number of Stanford maps")
@click.option("--rumsey", default=20, help="Number of Rumsey maps")
@click.option("--max-width", default=4096, help="Max image width")
@click.pass_context
def run_all(ctx: click.Context, stanford: int, rumsey: int, max_width: int) -> None:
    """Run the full pipeline: harvest -> download -> ocr -> index."""
    click.echo("=" * 60)
    click.echo("STEP 1: Harvest")
    click.echo("=" * 60)
    ctx.invoke(harvest, stanford=stanford, rumsey=rumsey)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 2: Download")
    click.echo("=" * 60)
    ctx.invoke(download, max_width=max_width)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 3: OCR")
    click.echo("=" * 60)
    ctx.invoke(ocr)

    click.echo("\n" + "=" * 60)
    click.echo("STEP 4: Index")
    click.echo("=" * 60)
    ctx.invoke(index)

    click.echo("\nPipeline complete! Use 'unimap search <query>' to search.")


@main.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(host: str, port: int, debug: bool) -> None:
    """Start the web viewer with IIIF manifest processing API."""
    from unimap.server import create_app

    app = create_app()
    click.echo(f"Starting UniMap viewer at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
