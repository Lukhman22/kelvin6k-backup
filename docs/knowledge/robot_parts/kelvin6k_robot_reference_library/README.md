# Kelvin6K Robot Reference Images — Initial Library

This folder contains four user-provided, whole-machine reference photos for internal Kelvin6K troubleshooting/RAG development.

## Important scope and limitations

- These images show overall machine/product appearance, not verified close-ups of electronics, drives, sensors, cables, pumps, or other individual components.
- Do not infer exact hardware variants, wiring, part numbers, dimensions, or manufacturer specifications from these images.
- Treat the images as **UNVERIFIED visual references** until a project engineer confirms the machine/version and source.
- The original publication/source of each supplied image has not been independently verified. Retain attribution/source details if they become available.
- These are reference photos, not incident images and not annotations. Never display them as the annotated version of an operator's incident upload.
- `image(20261015-101604).png` was a WhatsApp conversation screenshot, so it is intentionally excluded from this machine-image folder.

## Suggested workspace location

Copy this directory into the repository so the resulting path is:

`docs/knowledge/robot_parts/kelvin6k_robot_reference_library/`

If the project already has an established knowledge asset directory or ingestion manifest, use that existing convention instead of creating a competing library. Keep the image filenames and manifest paths in sync if moving the folder.

## Ingestion

Do not assume these images are usable by runtime RAG just because they exist on disk. Use the current Kelvin6K ingestion/indexing pipeline. Each image should have a stable ID, metadata, source/provenance, a file hash, and a persistent retrievable path. Make ingestion repeatable and deduplicate on hash/ID.

For visual matching, ensure the selected image is actually passed to a vision-capable model or supported image-retrieval flow. Text-only RAG over filenames/descriptions is not visual image understanding.

See `manifest.json` for initial, deliberately conservative descriptions and `GEMINI_IMPLEMENTATION_PROMPT.md` for the implementation task.
