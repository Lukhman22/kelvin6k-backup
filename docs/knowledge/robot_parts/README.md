# Kelvin6K Robot Reference & Component Image Library

This directory establishes the authoritative, persistent knowledge base of robot component schematics, whole-machine visual reference photographs, and technical specification sources for Kelvin6K.

---

## 1. Directory Structure

```text
docs/knowledge/robot_parts/
├── manifest.json                     # Master library catalog linking all reference assets
├── README.md                         # Architecture, addition, validation, and ingestion guide
├── kelvin6k_robot_reference_library/ # Whole-machine visual references
│   ├── manifest.json                 # Dedicated manifest for whole-machine photos
│   └── images/                       # High-resolution PNG reference photographs
│       ├── K6K-REF-001-outdoor-gantry-robot.png
│       ├── K6K-REF-002-mobile-concrete-printing-robot.png
│       ├── K6K-REF-003-exhibition-robot-side-view.png
│       └── K6K-REF-004-website-hero-robot.png
└── technical_specs/                  # Technical specification tables & documentation
    ├── atom_technical_specs.json     # Structured JSON specifications
    ├── atom_technical_specs.md       # Comparative Markdown documentation
    └── source_images/                # Authoritative ground-truth table captures
        ├── atom_robot_details_table.png
        └── atom_safety_connectivity_table_zoom.png
```

Component CAD and schematic references are additionally preserved under `data/reference_parts/`.

---

## 2. Separation of Image Roles

Kelvin6K maintains strict separation between five distinct image roles:

| Image Role | Purpose | Storage & Lineage | Display Label |
| :--- | :--- | :--- | :--- |
| `robot_reference` | Whole-machine visual references (overview, mobility, gantry) | `docs/knowledge/robot_parts/kelvin6k_robot_reference_library/images/` | **Robot Reference Photo** |
| `component_reference` | Targeted CAD/schematic diagrams of individual assemblies (nozzle, pump, hose) | `data/reference_parts/` / SQLite `component_references` | **Component Reference** |
| `technical_spec_source` | Ground-truth technical specification tables | `docs/knowledge/robot_parts/technical_specs/source_images/` | **Technical Specification Source** |
| `incident_original` | Original unannotated photograph uploaded by an operator | SQLite `incident_images` (`data/incident_images/`) | **Original Upload** |
| `incident_annotation` | Generated visual defect annotation overlay (boxes, contours, pills) | SQLite `incident_images` (`data/incident_images/`) | **AI Observation / Defect Annotation** |

> [!CAUTION]
> A `robot_reference` or `component_reference` image must **NEVER** be returned under the label *"Annotated Image"*.

---

## 3. How to Add New Reference Images

To add a new component or robot reference image:

1. **Place the Image File**:
   - For whole-machine visual references: place in `docs/knowledge/robot_parts/kelvin6k_robot_reference_library/images/`.
   - For component CAD / schematics: place in `data/reference_parts/`.
   - For specification captures: place in `docs/knowledge/robot_parts/technical_specs/source_images/`.
2. **Assign a Stable Identifier**:
   - Format: `K6K-REF-XXX` (for whole-machine photos), `REF-COMPONENT-XX` (for component schematics), or `ATOM-SPEC-XXX` (for specifications).
3. **Register Metadata in `manifest.json`**:
   - Provide `asset_id`, `component_name`, `display_title`, `image_category`, `source_type`, `verification_status`, `keywords`, and `limitations`.
4. **Run the Ingestion Pipeline**:
   ```bash
   PYTHONPATH=. .venv/bin/python -c 'from agent import incident_store; incident_store.init_reference_library()'
   ```
   The ingestion process calculates the SHA-256 content hash of every file, validates image magic bytes and dimensions using OpenCV, and registers the asset in SQLite without duplicating existing records.
