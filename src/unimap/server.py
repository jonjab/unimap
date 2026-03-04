"""Web server for UniMap viewer with IIIF manifest processing API."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from unimap.config import DATA_DIR, GEOJSON_DIR, ensure_dirs

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
app = Flask(__name__, static_folder=None)

# Job tracking: {job_id: {"status": "processing"|"done"|"error", ...}}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# Limit to one concurrent OCR job (PaddlePaddle is CPU-bound)
_processing_semaphore = threading.Semaphore(1)

# Lazy-loaded PaddleSpotter singleton
_spotter = None
_spotter_lock = threading.Lock()


def _get_spotter():
    global _spotter
    if _spotter is None:
        with _spotter_lock:
            if _spotter is None:
                from unimap.ocr.paddle_spotter import PaddleSpotter

                _spotter = PaddleSpotter()
                _spotter.warmup()
    return _spotter


def _manifest_to_id(manifest_url: str) -> str:
    return hashlib.sha256(manifest_url.encode()).hexdigest()[:12]


# --- Static file serving ---


@app.route("/")
def index():
    return send_from_directory(PROJECT_ROOT, "viewer.html")


@app.route("/data/<path:filepath>")
def serve_data(filepath):
    return send_from_directory(DATA_DIR.resolve(), filepath)


# --- API ---


@app.route("/api/maps")
def list_maps():
    """List all available processed maps from geojson files on disk."""
    maps = []
    if not GEOJSON_DIR.exists():
        return jsonify(maps)
    for gj_path in sorted(GEOJSON_DIR.glob("*.geojson")):
        try:
            with open(gj_path) as f:
                data = json.load(f)
            props = data.get("properties", {})
            slug = gj_path.stem
            source = props.get("map_source", "unknown")
            meta = props.get("metadata", {})
            maps.append({
                "slug": slug,
                "title": props.get("map_title", slug),
                "source": source,
                "total_detections": props.get("total_detections", 0),
                "creator": meta.get("creator", ""),
                "date": meta.get("date", ""),
                "description": meta.get("description", ""),
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipping %s: %s", gj_path, e)
    return jsonify(maps)


@app.route("/api/process", methods=["POST"])
def process_manifest():
    """Accept a IIIF manifest URL and run the full pipeline in a background thread."""
    body = request.get_json(silent=True)
    if not body or "manifest_url" not in body:
        return jsonify({"error": "Missing 'manifest_url' in request body"}), 400

    manifest_url = body["manifest_url"].strip()
    if not manifest_url.startswith("http"):
        return jsonify({"error": "Invalid URL"}), 400

    job_id = _manifest_to_id(manifest_url)

    with _jobs_lock:
        existing = _jobs.get(job_id)
        if existing and existing["status"] == "processing":
            return jsonify({"job_id": job_id, "status": "processing"}), 202
        if existing and existing["status"] == "done":
            return jsonify({"job_id": job_id, **existing}), 200
        _jobs[job_id] = {"status": "processing"}

    thread = threading.Thread(target=_run_pipeline, args=(job_id, manifest_url), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/api/process/<job_id>")
def get_job_status(job_id):
    """Poll for job completion status."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Unknown job"}), 404
    return jsonify({"job_id": job_id, **job})


def _run_pipeline(job_id: str, manifest_url: str) -> None:
    """Execute: parse manifest -> download -> OCR -> geojson."""
    import httpx

    from unimap.download.iiif import download_image
    from unimap.harvest.iiif import parse_iiif_manifest
    from unimap.harvest.models import MapRecord
    from unimap.ocr.patchify import run_ocr_on_map
    from unimap.output.geojson import write_geojson

    try:
        with _processing_semaphore:
            # Step 1: Parse manifest
            with httpx.Client(follow_redirects=True) as client:
                iiif_info = parse_iiif_manifest(client, manifest_url)

            if iiif_info is None:
                with _jobs_lock:
                    _jobs[job_id] = {"status": "error", "error": "Failed to parse IIIF manifest"}
                return

            # Step 2: Build record
            record = MapRecord(
                id=job_id,
                source="custom",
                title=iiif_info.get("title", "Untitled"),
                iiif_manifest_url=manifest_url,
                iiif_image_service_url=iiif_info["image_service_url"],
                canvas_id=iiif_info["canvas_id"],
                canvas_width=iiif_info["canvas_width"],
                canvas_height=iiif_info["canvas_height"],
                metadata={"manifest_url": manifest_url},
            )

            # Step 3: Download image
            image_path = download_image(record)

            # Step 4: OCR
            spotter = _get_spotter()
            result = run_ocr_on_map(record, image_path, spotter)

            # Step 5: Write geojson
            write_geojson(record, result)

            with _jobs_lock:
                _jobs[job_id] = {
                    "status": "done",
                    "slug": record.slug,
                    "title": record.title,
                    "detections": len(result.detections),
                }

    except Exception as e:
        logger.exception("Pipeline failed for %s", manifest_url)
        with _jobs_lock:
            _jobs[job_id] = {"status": "error", "error": str(e)}


def create_app() -> Flask:
    ensure_dirs()
    return app
