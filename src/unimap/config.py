"""Central configuration for paths and constants."""
from pathlib import Path

DATA_DIR = Path("data")
MANIFESTS_DIR = DATA_DIR / "manifests"
IMAGES_DIR = DATA_DIR / "images"
PATCHES_DIR = DATA_DIR / "patches"
OCR_RAW_DIR = DATA_DIR / "ocr_raw"
GEOJSON_DIR = DATA_DIR / "geojson"
ANNOTATIONS_DIR = DATA_DIR / "annotations"
SQLITE_DB = DATA_DIR / "unimap.db"

# Harvesting
STANFORD_LAYERS_URL = (
    "https://raw.githubusercontent.com/OpenGeoMetadata/edu.stanford.purl/main/layers.json"
)
STANFORD_METADATA_BASE = (
    "https://raw.githubusercontent.com/OpenGeoMetadata/edu.stanford.purl/main"
)
STANFORD_IIIF_REF_KEY = "http://iiif.io/api/presentation#manifest"

RUMSEY_SEARCH_URL = "https://www.davidrumsey.com/luna/servlet/as/search"

# Patching
PATCH_SIZE = 1000
PATCH_OVERLAP = 200

# Download
MAX_IMAGE_WIDTH = 4096
DOWNLOAD_TIMEOUT = 120

# OCR
PADDLE_LANG = "en"
PADDLE_USE_GPU = False
CONFIDENCE_THRESHOLD = 0.5


def ensure_dirs() -> None:
    for d in [
        MANIFESTS_DIR / "stanford",
        MANIFESTS_DIR / "rumsey",
        IMAGES_DIR / "stanford",
        IMAGES_DIR / "rumsey",
        PATCHES_DIR,
        OCR_RAW_DIR,
        GEOJSON_DIR,
        ANNOTATIONS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)
