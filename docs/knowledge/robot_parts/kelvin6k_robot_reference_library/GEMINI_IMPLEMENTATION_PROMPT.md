# Prompt for Gemini / AGY / Antigravity coding agent

Implement the Kelvin6K robot-reference image library in the existing repository. First confirm the actual repository root and inspect the current RAG ingestion pipeline, database schema, image storage, API endpoints, assistant/query router, and frontend image cards. Do not assume a specific ingestion command or create a duplicate RAG system.

The reference images are located at:
`docs/knowledge/robot_parts/kelvin6k_robot_reference_library/`

Files:
- `README.md`
- `manifest.json`
- `images/K6K-REF-001-outdoor-gantry-robot.png`
- `images/K6K-REF-002-mobile-concrete-printing-robot.png`
- `images/K6K-REF-003-exhibition-robot-side-view.png`
- `images/K6K-REF-004-website-hero-robot.png`

## Required behaviour

1. Ingest the manifest and image assets through the existing project ingestion/indexing path. Make ingestion idempotent, validate file existence and decodability, calculate or retain content hashes, and avoid duplicate records.
2. Store stable asset IDs, relative paths, captions, visual observations, source/provenance, and verification status. Resolve paths safely relative to the configured asset root; do not trust arbitrary paths supplied by chat input.
3. Treat every initial asset as UNVERIFIED and as a whole-machine/product-appearance reference. These four images do not show enough detail to assert specific electronics, sensor models, drive part numbers, wiring layouts, fault causes, or exact machine version.
4. In Kelvin's RAG/troubleshooting flow, retrieve relevant historical incidents and text knowledge first, then retrieve matching reference-image metadata when relevant. If visual comparison is needed, pass the selected image itself to an available vision-capable runtime model or supported visual retrieval mechanism. Do not claim that a text-only search has visually inspected the image.
5. Keep three asset roles distinct: `original_incident`, `annotated_incident`, and `component_reference`. Never show a reference photo under an “Annotated Image” heading, and never substitute a reference asset when an annotation is missing.
6. When displaying a reference image, identify it as a reference and explain why it may be relevant. Phrase conclusions as possible matches unless supported by verified documentation or direct evidence. If the stored images do not provide a relevant view, say so and request a close-up rather than inventing a match.
7. Keep reference images separate from runtime incident uploads. Use repository-tracked files for these approved reference assets if consistent with the existing project; do not commit incident uploads, databases, secrets, or private runtime content.
8. Expose structured image metadata/URLs in the existing response contract so the frontend can render the correct image, label, caption, source and verification state. Ensure image endpoints return actual bytes and proper MIME types.
9. Add tests for ingestion, deduplication, missing/corrupt assets, asset-role separation, retrieval relevance, conservative unverified wording, and correct image URL/byte serving.
10. Preserve attendance, wall-production recording, voice controls, existing conversation history, and current RAG behaviour. Do not issue physical robot commands or start camera-model training in this task.

## Acceptance tests

- Ask “Show me the Kelvin6K robot reference images.” The application displays only the indexed reference assets with accurate labels.
- Ask “Which part may be responsible for this error?” with an error code or symptom. Kelvin retrieves relevant documented evidence and displays a reference only when relevant; it does not claim component-level identification from a distant whole-machine photo.
- Upload a defect photo. The original and its annotation remain distinct from the reference library.
- Restart the backend. The references remain available.
- Run the existing relevant backend tests and frontend build. Report exact commands and results.

Before modifying code, report a short audit of the current pipeline and an implementation plan. After implementation, provide files changed, actual ingestion command, how to add future images, test results, and any limitations. Do not claim success unless verified.
