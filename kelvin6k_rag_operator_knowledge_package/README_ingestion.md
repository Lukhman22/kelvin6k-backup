# Kelvin6K RAG operator knowledge package

## Files
- `kelvin6k_operator_knowledge.jsonl`: one structured JSON record per issue, suitable for a custom ingestion pipeline after schema mapping.
- `operator_knowledge_review.md`: human-readable draft and RAG behavior rules.
- `engineer_validation_checklist.csv`: conflicts and machine-specific items requiring approval.

## Important
This package is based on the English Q&A/problem-solution summary provided by the user, attributed to a Hindi operator audio recording. The original audio was not independently transcribed in this preparation step.

## Before ingestion
1. Map JSON keys to the existing RAG ingestion schema; do not assume the agent accepts this JSONL schema directly.
2. Preserve `issue_id`, `source`, `status`, `confidence`, `verification_required`, and `safety_notes` as metadata if supported.
3. Keep unresolved machine-specific instructions behind a safety/review filter.
4. Review conflicts with an authorized engineer.
5. Test retrieval using the synthetic questions in the Markdown file.
6. Confirm citations/source traceability in assistant responses.

Do not execute any robot, pump, servo, encoder, or Z-axis actions from these records.
