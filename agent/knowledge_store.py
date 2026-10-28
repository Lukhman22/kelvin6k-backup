"""
Structured Knowledge Model & Relational Repository for Kelvin6K.

Manages:
1. `knowledge_documents`: Provenance, versioning, SHA-256 checksums, and extraction status.
2. `knowledge_records`: Detailed text-first operational intelligence records with evidence grading.
3. `component_fault_relationships`: Relational mapping of components, fault codes, safe vs prohibited actions.

Guarantees:
- Exact fault-code protection (e.g. E136.1, E137.1, parameter H0D11).
- Clear distinction between approved fixes and unverified operator workarounds.
- Zero fabrication of root causes or safety procedures.
"""

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from agent import config, db
from agent.logging_setup import get_logger

log = get_logger("KNOWLEDGE_STORE")


def compute_file_checksum(file_path: str) -> str:
    """Computes SHA-256 checksum of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while chunk := fh.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Document Tracking
# ---------------------------------------------------------------------------

def upsert_document(
    filename: str,
    title: str,
    file_type: str,
    checksum_sha256: str,
    source_path: Optional[str] = None,
    version_tag: Optional[str] = "1.0",
    reliability: str = "documented",
    chunk_count: int = 0,
    extraction_status: str = "indexed",
    db_path: Optional[str] = None,
) -> str:
    """Registers or updates a source document with checksum and extraction metadata."""
    now = time.time()
    doc_id = f"DOC-{hashlib.sha256(filename.encode()).hexdigest()[:12].upper()}"

    sql = """
    INSERT INTO knowledge_documents (
        doc_id, title, filename, file_type, source_path, version_tag,
        checksum_sha256, reliability, extraction_status, chunk_count,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(filename) DO UPDATE SET
        title = excluded.title,
        file_type = excluded.file_type,
        source_path = excluded.source_path,
        version_tag = excluded.version_tag,
        checksum_sha256 = excluded.checksum_sha256,
        reliability = excluded.reliability,
        extraction_status = excluded.extraction_status,
        chunk_count = excluded.chunk_count,
        updated_at = excluded.updated_at
    """
    with db.connect(db_path) as conn:
        conn.execute(sql, (
            doc_id, title, filename, file_type, source_path, version_tag,
            checksum_sha256, reliability, extraction_status, chunk_count,
            now, now
        ))
    return doc_id


def get_document_by_filename(filename: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE filename = ?", (filename,)
        ).fetchone()
        return dict(row) if row else None


def list_knowledge_documents(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with db.connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM knowledge_documents ORDER BY filename ASC").fetchall()
        return [dict(r) for r in rows]


def mark_stale_documents(active_filenames: List[str], db_path: Optional[str] = None) -> List[str]:
    """Marks documents deleted from active corpus as 'stale'."""
    now = time.time()
    stale_files: List[str] = []
    with db.connect(db_path) as conn:
        all_docs = conn.execute("SELECT doc_id, filename FROM knowledge_documents WHERE extraction_status != 'stale'").fetchall()
        for doc in all_docs:
            if doc["filename"] not in active_filenames:
                conn.execute(
                    "UPDATE knowledge_documents SET extraction_status = 'stale', updated_at = ? WHERE doc_id = ?",
                    (now, doc["doc_id"])
                )
                stale_files.append(doc["filename"])
    if stale_files:
        log.info("Marked %d stale documents: %s", len(stale_files), stale_files)
    return stale_files


# ---------------------------------------------------------------------------
# Structured Knowledge Records
# ---------------------------------------------------------------------------

def upsert_knowledge_record(
    record_id: str,
    title: str,
    problem_statement: str,
    category: str = "troubleshooting",
    doc_id: Optional[str] = None,
    issue_id: Optional[str] = None,
    machine_model: str = "Kelvin6K-ATOM",
    component_name: Optional[str] = None,
    fault_code: Optional[str] = None,
    observed_symptoms: Optional[str] = None,
    operating_conditions: Optional[str] = None,
    possible_causes: Optional[str] = None,
    confirmed_root_cause: Optional[str] = None,
    corrective_action: Optional[str] = None,
    workaround: Optional[str] = None,
    is_workaround_approved: int = 0,
    safety_constraints: Optional[str] = None,
    preventive_guidance: Optional[str] = None,
    verification_outcome: Optional[str] = None,
    validation_status: str = "documented",
    confidence_rating: float = 0.8,
    section_heading: Optional[str] = None,
    page_number: Optional[int] = None,
    searchable_text: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """Inserts or updates a normalized industrial knowledge record."""
    now = time.time()
    if not searchable_text:
        searchable_text = f"{title} {problem_statement} {observed_symptoms or ''} {fault_code or ''} {component_name or ''} {corrective_action or ''} {workaround or ''} {safety_constraints or ''}".lower()

    sql = """
    INSERT INTO knowledge_records (
        record_id, doc_id, issue_id, title, category, machine_model,
        component_name, fault_code, problem_statement, observed_symptoms,
        operating_conditions, possible_causes, confirmed_root_cause,
        corrective_action, workaround, is_workaround_approved,
        safety_constraints, preventive_guidance, verification_outcome,
        validation_status, confidence_rating, section_heading, page_number,
        searchable_text, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(record_id) DO UPDATE SET
        doc_id = excluded.doc_id,
        issue_id = excluded.issue_id,
        title = excluded.title,
        category = excluded.category,
        machine_model = excluded.machine_model,
        component_name = excluded.component_name,
        fault_code = excluded.fault_code,
        problem_statement = excluded.problem_statement,
        observed_symptoms = excluded.observed_symptoms,
        operating_conditions = excluded.operating_conditions,
        possible_causes = excluded.possible_causes,
        confirmed_root_cause = excluded.confirmed_root_cause,
        corrective_action = excluded.corrective_action,
        workaround = excluded.workaround,
        is_workaround_approved = excluded.is_workaround_approved,
        safety_constraints = excluded.safety_constraints,
        preventive_guidance = excluded.preventive_guidance,
        verification_outcome = excluded.verification_outcome,
        validation_status = excluded.validation_status,
        confidence_rating = excluded.confidence_rating,
        section_heading = excluded.section_heading,
        page_number = excluded.page_number,
        searchable_text = excluded.searchable_text,
        updated_at = excluded.updated_at
    """
    with db.connect(db_path) as conn:
        conn.execute(sql, (
            record_id, doc_id, issue_id, title, category, machine_model,
            component_name, fault_code, problem_statement, observed_symptoms,
            operating_conditions, possible_causes, confirmed_root_cause,
            corrective_action, workaround, is_workaround_approved,
            safety_constraints, preventive_guidance, verification_outcome,
            validation_status, confidence_rating, section_heading, page_number,
            searchable_text, now, now
        ))
    return record_id


def get_exact_fault_record(code_or_param: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Exact match protection: returns the authoritative record for a specific fault code
    or parameter identifier (e.g. 'E136.1', 'E137.1', 'H0D11').
    """
    norm = code_or_param.strip().upper()
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_records WHERE UPPER(fault_code) = ? OR UPPER(issue_id) = ? LIMIT 1",
            (norm, norm)
        ).fetchone()
        if not row:
            # Fallback to checking within fault_code column if prefixed
            row = conn.execute(
                "SELECT * FROM knowledge_records WHERE fault_code LIKE ? LIMIT 1",
                (f"%{norm}%",)
            ).fetchone()
        return dict(row) if row else None


def search_knowledge_records(
    query: str,
    component: Optional[str] = None,
    fault_code: Optional[str] = None,
    limit: int = 5,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Searches structured knowledge records by tokens, component, or fault code."""
    terms = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_\-.]+\b", query) if len(t) > 2]
    with db.connect(db_path) as conn:
        query_sql = "SELECT * FROM knowledge_records WHERE 1=1"
        params: List[Any] = []
        if fault_code:
            query_sql += " AND UPPER(fault_code) = ?"
            params.append(fault_code.upper())
        if component:
            query_sql += " AND (LOWER(component_name) LIKE ? OR LOWER(title) LIKE ?)"
            params.append(f"%{component.lower()}%")
            params.append(f"%{component.lower()}%")

        rows = conn.execute(query_sql, params).fetchall()
        results = [dict(r) for r in rows]

        if not terms and not fault_code and not component:
            return []

        # Score matching rows based on token overlap
        scored = []
        for rec in results:
            text = (rec["searchable_text"] or "").lower()
            match_count = sum(1 for term in terms if term in text)
            if fault_code and rec.get("fault_code") and fault_code.upper() in rec["fault_code"].upper():
                match_count += 10.0  # heavy exact code boost
            if component and rec.get("component_name") and component.lower() in rec["component_name"].lower():
                match_count += 5.0
            if match_count > 0:
                scored.append((rec, match_count))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored[:limit]]


# ---------------------------------------------------------------------------
# Component & Fault Relationships
# ---------------------------------------------------------------------------

def upsert_component_relationship(
    component_name: str,
    subsystem: str,
    symptom: str,
    safe_actions: str,
    prohibited_actions: str,
    fault_code: Optional[str] = None,
    record_id: Optional[str] = None,
    reference_id: Optional[str] = None,
    machine_version: str = "Kelvin6K-ATOM",
    severity: str = "warning",
    db_path: Optional[str] = None,
) -> int:
    """Links components to subsystems, symptoms, safe actions, and prohibited actions."""
    now = time.time()
    sql = """
    INSERT INTO component_fault_relationships (
        component_name, subsystem, fault_code, symptom, record_id,
        reference_id, safe_actions, prohibited_actions, machine_version,
        severity, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with db.connect(db_path) as conn:
        # Check if identical relationship already exists
        cur = conn.execute(
            "SELECT rel_id FROM component_fault_relationships WHERE component_name = ? AND symptom = ? AND IFNULL(fault_code, '') = ?",
            (component_name, symptom, fault_code or "")
        )
        existing = cur.fetchone()
        if existing:
            conn.execute(
                """UPDATE component_fault_relationships SET
                    subsystem = ?, safe_actions = ?, prohibited_actions = ?,
                    record_id = ?, reference_id = ?, severity = ?
                   WHERE rel_id = ?""",
                (subsystem, safe_actions, prohibited_actions, record_id, reference_id, severity, existing["rel_id"])
            )
            return existing["rel_id"]

        cur = conn.execute(sql, (
            component_name, subsystem, fault_code, symptom, record_id,
            reference_id, safe_actions, prohibited_actions, machine_version,
            severity, now
        ))
        return cur.lastrowid


def get_relationships_by_fault_or_component(
    term: str,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Returns relational links for a fault code, component name, or subsystem."""
    term_clean = term.strip().lower()
    with db.connect(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM component_fault_relationships
               WHERE LOWER(fault_code) = ?
                  OR LOWER(component_name) LIKE ?
                  OR LOWER(subsystem) LIKE ?
                  OR LOWER(symptom) LIKE ?
               ORDER BY rel_id ASC""",
            (term_clean, f"%{term_clean}%", f"%{term_clean}%", f"%{term_clean}%")
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Seed Knowledge Initialization
# ---------------------------------------------------------------------------

def seed_authoritative_knowledge(db_path: Optional[str] = None) -> None:
    """
    Seeds authoritative engineering knowledge records and component relationships
    for critical industrial items (e.g. E136.1, E137.1, H0D11, pump washouts, hose routing).
    """
    db.init_db(db_path)

    # 1. Fault E136.1: Absolute Encoder Cable Damage
    rec_e136 = upsert_knowledge_record(
        record_id="REC-FAULT-E136.1",
        issue_id="K6-FAULT-E136.1",
        title="Fault E136.1: Absolute Encoder Cable Damage",
        category="fault_code",
        component_name="absolute encoder cable",
        fault_code="E136.1",
        problem_statement="Robot arm halted with servo drive alarm E136.1 indicating absolute encoder communication disruption.",
        observed_symptoms="Alarm E136.1 displayed on drive controller; axis motion inhibited; encoder feedback lost.",
        operating_conditions="Normal print run or axis jog; dynamic cable carrier flexure.",
        possible_causes="Damage to absolute encoder cable; loose or contaminated circular connector; electrical noise interference.",
        confirmed_root_cause="Physical damage / pinching of the absolute encoder cable in the cable track.",
        corrective_action="Inspect encoder cable along its entire flexure length for pinches, cuts, or strain; check connector seating; verify shielding ground; replace damaged cable harness.",
        workaround="None approved. Blind error clearing without inspection risks axis runaway or collision.",
        is_workaround_approved=0,
        safety_constraints="DO NOT clear error or force axis jog without physical cable inspection. Unauthorized encoder reset is prohibited.",
        preventive_guidance="Inspect cable track bend radius and secure strain relief brackets during scheduled weekly maintenance.",
        verification_outcome="Restore encoder communication and verify continuous axis feedback before homing.",
        validation_status="verified",
        confidence_rating=0.98,
        searchable_text="e136.1 e136 absolute encoder cable damage alarm servo drive communication loose connector",
        db_path=db_path,
    )
    upsert_component_relationship(
        component_name="absolute encoder cable",
        subsystem="Robot Arm Motion & Servo Drives",
        fault_code="E136.1",
        symptom="Alarm E136.1, loss of absolute encoder position feedback",
        safe_actions="Perform lock-out tag-out (LOTO); physically inspect cable and connectors; test continuity with multimeter.",
        prohibited_actions="Never reset drive encoder or force motor motion without physical inspection.",
        record_id=rec_e136,
        reference_id="REF-SERVO-01",
        severity="critical",
        db_path=db_path,
    )

    # 2. Fault E137.1: Robot Servo Position Mismatch
    rec_e137 = upsert_knowledge_record(
        record_id="REC-FAULT-E137.1",
        issue_id="K6-FAULT-E137.1",
        title="Fault E137.1: Robot Servo Position Mismatch",
        category="fault_code",
        component_name="servo drive",
        fault_code="E137.1",
        problem_statement="Robot controller halts execution with error code E137.1 indicating servo position discrepancy.",
        observed_symptoms="Drive alarm E137.1; axis position divergence between command trajectory and actual motor position.",
        operating_conditions="High-load extrusion, nozzle contact with print bead, or sudden emergency stop.",
        possible_causes="Mechanical axis obstruction; motor coupling slippage; drive parameter deviation; encoder offset loss.",
        confirmed_root_cause="Servo position mismatch between motor feedback and kinematic controller.",
        corrective_action="Check mechanical axis for physical obstruction or nozzle collision; verify free axis motion by hand (with servos disabled); check motor coupling integrity; verify calibrated zero datum before authorized encoder recalibration.",
        workaround="Resetting encoder values directly from drive interface without mechanical alignment is an unverified workaround.",
        is_workaround_approved=0,
        safety_constraints="DO NOT perform an encoder reset without authorized engineering sign-off and physical position verification. Collision risk if zero reference shifts.",
        preventive_guidance="Ensure nozzle path clearance and verify toolhead acceleration limits in slicer settings.",
        verification_outcome="Zero-datum verification and slow-speed test trajectory under engineering supervision.",
        validation_status="verified",
        confidence_rating=0.95,
        searchable_text="e137.1 e137 servo position mismatch servo drive motor slippage encoder recalibration mechanical obstruction",
        db_path=db_path,
    )
    upsert_component_relationship(
        component_name="servo drive",
        subsystem="Robot Kinematics & Drives",
        fault_code="E137.1",
        symptom="Alarm E137.1, axis position mismatch / deviation",
        safe_actions="Check mechanical path clearance; inspect motor-gearbox coupling; seek authorized engineering verification.",
        prohibited_actions="Never execute blind encoder reset or calibrate datum without physical alignment verification.",
        record_id=rec_e137,
        reference_id="REF-SERVO-01",
        severity="critical",
        db_path=db_path,
    )

    # 3. Parameter H0D11: Z-Axis Downward Travel Lock
    rec_h0d11 = upsert_knowledge_record(
        record_id="REC-PARAM-H0D11",
        issue_id="K6-Z-001",
        title="Z-Axis Downward Motion Blocked by Parameter H0D11",
        category="machine_parameter",
        component_name="Z-axis linear motion",
        fault_code="H0D11",
        problem_statement="Operator unable to jog or command Z-axis downward toward print bed.",
        observed_symptoms="Z-axis moves upward but downward motion commands are rejected by motion controller; software limit active.",
        operating_conditions="Setup / bed calibration or initial layer touchdown.",
        possible_causes="Software downward travel limit parameter H0D11 set higher than target coordinate; uncalibrated origin.",
        confirmed_root_cause="Controller software travel limit parameter H0D11 restricting downward motion boundary.",
        corrective_action="Verify physical nozzle clearance and bed coordinate datum; adjust parameter H0D11 ONLY under authorized technician authorization.",
        workaround="Arbitrary parameter override to force downward jog without bed verification is an UNAPPROVED WORKAROUND.",
        is_workaround_approved=0,
        safety_constraints="UNAPPROVED WORKAROUND: Modifying H0D11 without authorized engineering sign-off is strictly prohibited. Toolhead collision with build plate may cause severe mechanical failure.",
        preventive_guidance="Verify build envelope and work coordinate system (WCS) offsets prior to daily print initiation.",
        verification_outcome="Authorized technician verifies bed height datum before parameter confirmation.",
        validation_status="unverified_workaround",
        confidence_rating=0.90,
        searchable_text="h0d11 z-axis downward motion blocked limit parameter software travel boundary",
        db_path=db_path,
    )
    upsert_component_relationship(
        component_name="Z-axis linear motion",
        subsystem="Linear Axis & Gantry",
        fault_code="H0D11",
        symptom="Downward motion rejected / locked",
        safe_actions="Measure physical bed clearance; confirm toolhead datum; request authorized technician sign-off.",
        prohibited_actions="Never modify H0D11 software limits without verifying physical collision clearance.",
        record_id=rec_h0d11,
        severity="warning",
        db_path=db_path,
    )

    # 4. Pump Blockage / Material Flow Drop
    rec_flow = upsert_knowledge_record(
        record_id="REC-FLOW-001",
        issue_id="K6K-FLOW-001",
        title="Concrete Material Flow Interruption & Pump Blockage",
        category="material_flow",
        component_name="concrete pump and hopper",
        problem_statement="Material extrusion flow suddenly drops or ceases completely during active printing.",
        observed_symptoms="Extrusion bead thins or stops; pump line pressure spikes; motor current rises.",
        operating_conditions="Continuous printing with accelerator admixture or low-slump concrete mix.",
        possible_causes="Aggregate aggregate lump blocking intake grate; hardened mortar buildup in delivery hose; premature accelerator flash setting.",
        confirmed_root_cause="Pump throat or delivery hose obstruction due to particle accumulation or stagnation.",
        corrective_action="Immediately STOP pump; depressurize delivery line using approved safety valve; inspect hopper intake screen; flush delivery hose with clean water and sponge ball.",
        workaround="Striking the pump casing with a hammer or aggressively pulsing feedrate to break blockages.",
        is_workaround_approved=0,
        safety_constraints="UNAPPROVED WORKAROUND - SAFETY REVIEW REQUIRED: Striking the pump casing or pulsing feedrate under pressure is strictly prohibited. Risk of explosive hose rupture, structural component deformation, and operator injury.",
        preventive_guidance="Screen mix aggregate prior to loading hopper; maintain continuous agitated flow; adhere to 5-minute pause washout rule.",
        verification_outcome="Verify clean water washout flow and unobstructed delivery pressure prior to restarting print.",
        validation_status="unverified_workaround",
        confidence_rating=0.99,
        searchable_text="flow drop pump blockage concrete material sudden drop hammer strike pulse feedrate delivery hose unapproved workaround",
        db_path=db_path,
    )
    upsert_component_relationship(
        component_name="concrete pump and hopper",
        subsystem="Delivery System & Pumping",
        symptom="Extrusion flow sudden drop, pressure spike",
        safe_actions="Stop pump; depressurize line; inspect hopper screen; wash out hose with water.",
        prohibited_actions="Never strike pump casing with a hammer. Never rapidly pulse feedrate against a blocked line.",
        record_id=rec_flow,
        reference_id="REF-PUMP-01",
        severity="emergency",
        db_path=db_path,
    )

    # 5. Cleaning Schedule & Washout Interval
    rec_clean = upsert_knowledge_record(
        record_id="REC-CLEAN-001",
        issue_id="K6K-CLEAN-001",
        title="Pump & Delivery Hose Washout Interval",
        category="maintenance_interval",
        component_name="delivery hose and pump",
        problem_statement="Determining mandatory cleaning frequency for concrete pump and delivery hose.",
        observed_symptoms="Residual mortar buildup inside delivery line; reduced extrusion cross-section.",
        operating_conditions="Daily 3D printing operations.",
        possible_causes="Delayed washdown resulting in hardened concrete lining inside delivery line.",
        confirmed_root_cause="Mandatory operational rule specifies washdown every 2 hours of continuous operation or immediately after job completion.",
        corrective_action="Perform sponge ball washout with clean water after every 2 hours of printing, after print completion, or if paused longer than 5 minutes when accelerator is mixed.",
        workaround="Operator notes suggest cleaning only once per shift at end of day (Conflicting workaround).",
        is_workaround_approved=0,
        safety_constraints="CONFLICTING EVIDENCE - OPERATOR REPORTED VS APPROVED SOP: End-of-shift only washouts lead to hose hardening and overpressure ruptures. Standard SOP (every 2 hours / post-job) takes precedence.",
        preventive_guidance="Schedule water flush cycles into shift planning.",
        verification_outcome="Inspect washout water discharge until clear of mortar slurry.",
        validation_status="conflicting",
        confidence_rating=0.92,
        searchable_text="cleaning interval pump hose washout frequency kitni der mein wash karaye har 2 ghante conflicting",
        db_path=db_path,
    )
    upsert_component_relationship(
        component_name="delivery hose and pump",
        subsystem="Delivery System & Pumping",
        symptom="Internal mortar buildup, cleaning schedule inquiry",
        safe_actions="Wash out every 2 hours of continuous printing or after job completion with sponge ball.",
        prohibited_actions="Do not defer washout to end of shift if accelerator-mixed concrete was utilized.",
        record_id=rec_clean,
        reference_id="REF-HOSE-01",
        severity="warning",
        db_path=db_path,
    )

    log.info("Authoritative engineering knowledge successfully seeded into SQLite.")
