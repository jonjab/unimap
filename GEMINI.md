# GEMINI.md - UniMap Project Context

## Project Overview

The **UniMap** project is a Python-based application designed for processing, indexing, and visualizing map data, particularly historical maps enhanced with OCR (Optical Character Recognition) results. It aims to provide a comprehensive workflow from data acquisition to interactive viewing.

**Key Features:**
*   **Data Harvesting:** Supports fetching data from various sources, including IIIF (International Image Interoperability Framework) manifests, Stanford University's digital collections, and Rumsey Map Collection.
*   **OCR Processing:** Integrates OCR capabilities, specifically mentioning support for PaddlePaddle models (`paddle_spotter.py`, `spotter_v2.py`) to detect and recognize text on map images.
*   **Data Indexing:** Creates indexes (e.g., `sqlite_index.py`) for efficient searching of OCR results.
*   **Interactive Viewer:** A web-based interface (`viewer.html`) to display map images with overlaid OCR text detections, confidence scores, and bounding boxes.

**Technologies:**
*   **Backend/Processing:** Python.
*   **Dependency Management:** `uv` (used via `Makefile` targets like `uv sync`, `uv run`).
*   **Testing:** `pytest` (invoked via `make test`).
*   **Linting:** `ruff` (invoked via `make lint`).
*   **Frontend:** HTML, CSS, and vanilla JavaScript for the `viewer.html`. Uses SVG for overlaying text detection boxes.

## Building and Running

The project is managed using a `Makefile` which orchestrates various tasks.

*   **Install Dependencies:**
    ```bash
    make install
    # or directly: uv sync
    ```

*   **Data Processing Pipeline:**
    *   **Harvest Data:** `make harvest`
    *   **Download Data:** `make download`
    *   **Perform OCR:** `make ocr` (can specify `--spotter paddle`)
    *   **Index Data:** `make index`
    *   **Run Full Pipeline:** `make run-all`

*   **Running the Viewer:**
    The `viewer.html` file is a standalone HTML application. To access it and its associated `data/` directory correctly, it's recommended to serve it using a simple HTTP server.
    ```bash
    # Navigate to the project root directory
    cd /home/coder/unimap
    # Serve the directory
    python -m http.server 8000
    ```
    Then, open `http://localhost:8000/viewer.html` in your browser.

*   **Testing:**
    ```bash
    make test
    # or directly: uv run pytest tests/ -v
    ```

*   **Linting:**
    ```bash
    make lint
    # or directly: uv run ruff check src/ tests/
    ```

*   **Cleaning:**
    *   `make clean`: Removes intermediate files (`data/patches`, `data/ocr_raw`).
    *   `make clean-all`: Removes all generated data (`data/`).

## Development Conventions

*   **Python:** Follows standard Python practices, with dependencies managed by `uv`.
*   **Code Style:** Linting is enforced using `ruff`.
*   **Testing:** Unit and integration tests are written using `pytest`.
*   **Frontend:** The web viewer uses vanilla JavaScript, HTML, and CSS, with SVG for dynamic overlays.

## Current Task: Fixing Zoom in Viewer

**Problem:**
The current map viewer (`viewer.html`) lacks interactive zoom functionality. While a `widthSlider` allows for manual scaling of the map and its overlays, it does not provide the smooth zooming and panning experience expected in an interactive map viewer.

**Plan:**
1.  **Analyze Viewer Implementation:** Examine the existing `viewer.html` script, specifically how the `widthSlider` affects the `mapImage` and `overlay` elements and how the `renderOverlay` function scales elements.
2.  **Implement Interactive Zoom:**
    *   **Option A (Enhance Existing):** Modify the `viewer.html` to:
        *   Add event listeners for the mouse wheel (`wheel` event) on the `.viewer` or `#mapImage` element.
        *   Adjust the scale factor based on the scroll direction and intensity.
        *   Update the `widthSlider` value (or a separate zoom level variable) accordingly.
        *   Re-render the overlay using the updated scale, ensuring the overlay remains correctly positioned relative to the scaled image.
        *   (Optional) Add explicit zoom-in/zoom-out buttons.
    *   **Option B (Integrate Library):** Introduce a JavaScript library like `Panzoom` for pan and zoom functionality. This would involve:
        *   Adding the library's script to `viewer.html` (e.g., via CDN).
        *   Initializing the library on the viewer container (`#viewer`).
        *   Ensuring the SVG overlay is correctly configured to pan and zoom alongside the image.
        *   Potentially adding UI controls for zoom.
3.  **Testing:** Thoroughly test the zoom and pan functionality, ensuring that the overlay remains aligned with the map features across all zoom levels. Verify performance and responsiveness.
