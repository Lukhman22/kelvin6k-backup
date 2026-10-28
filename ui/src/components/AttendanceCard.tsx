import { useEffect, useState } from "react";
import {
  checkInAttendance,
  checkOutAttendance,
  getAttendanceList,
  getOperators,
  createOperator,
  getWallProduction,
  recordWallProduction,
  correctWallProduction,
} from "../api";
import type { AttendanceRecord, Operator, WallProductionRecord, WallProductionTotal } from "../types";
import "./AttendanceCard.css";

export function AttendanceCard() {
  const [activeTab, setActiveTab] = useState<"attendance" | "production">("attendance");
  const [operators, setOperators] = useState<Operator[]>([]);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [selectedOp, setSelectedOp] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Employee State
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newRole, setNewRole] = useState("operator");

  // Wall Production State
  const [prodScope, setProdScope] = useState<"today" | "this_week" | "all_time">("today");
  const [wallTotals, setWallTotals] = useState<WallProductionTotal | null>(null);
  const [wallRecords, setWallRecords] = useState<WallProductionRecord[]>([]);
  const [prodOp, setProdOp] = useState<string>("");
  const [prodQuantity, setProdQuantity] = useState<number>(1);
  const [prodJobId, setProdJobId] = useState<string>("");
  const [prodNotes, setProdNotes] = useState<string>("");
  const [isSubmittingProd, setIsSubmittingProd] = useState(false);

  // Correction Modal State
  const [correctingRecord, setCorrectingRecord] = useState<WallProductionRecord | null>(null);
  const [correctedQty, setCorrectedQty] = useState<number>(1);
  const [correctionReason, setCorrectionReason] = useState<string>("");
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState(false);

  useEffect(() => {
    fetchOperators();
    fetchRecords();
    fetchWallData();

    // Refresh records periodically
    const timer = setInterval(() => {
      fetchRecords();
      fetchWallData();
    }, 60000);

    const handleAttendanceUpdated = () => {
      fetchRecords();
      fetchOperators();
      fetchWallData();
    };
    window.addEventListener("kelvin-attendance-updated", handleAttendanceUpdated);

    return () => {
      clearInterval(timer);
      window.removeEventListener("kelvin-attendance-updated", handleAttendanceUpdated);
    };
  }, [prodScope]);

  const fetchOperators = async () => {
    try {
      const res = await getOperators();
      setOperators(res.operators || []);
    } catch (err) {
      console.error("Failed to fetch operators:", err);
    }
  };

  const fetchRecords = async () => {
    try {
      const data = await getAttendanceList(); // Backend defaults to local today
      setRecords(data);
    } catch (err) {
      console.error("Failed to fetch attendance:", err);
    }
  };

  const fetchWallData = async () => {
    try {
      const data = await getWallProduction({ scope: prodScope, include_records: true });
      setWallTotals(data);
      setWallRecords(data.records || []);
    } catch (err) {
      console.error("Failed to fetch wall production:", err);
    }
  };

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "ADD_NEW") {
      setIsAdding(true);
      setSelectedOp("");
      setError(null);
    } else {
      setSelectedOp(val);
      setIsAdding(false);
    }
  };

  const handleAddEmployee = async () => {
    setError(null);
    setSuccessMsg(null);
    if (!newName.trim()) {
      setError("Employee name is required.");
      return;
    }
    try {
      const res = await createOperator({
        name: newName,
        employee_code: newCode.trim() || undefined,
        role: newRole,
        active: 1,
      });
      await fetchOperators();
      setIsAdding(false);
      setSelectedOp(res.operator_id);
      setNewName("");
      setNewCode("");
      const eidText = res.eid ? ` (ID: ${res.eid})` : "";
      setSuccessMsg(`Employee "${newName}"${eidText} registered successfully.`);
    } catch (err: any) {
      setError(err.message || "Failed to create employee.");
    }
  };

  const handleCancelAdd = () => {
    setIsAdding(false);
    setSelectedOp("");
    setNewName("");
    setNewCode("");
    setError(null);
  };

  const handleCheckIn = async () => {
    setError(null);
    setSuccessMsg(null);
    try {
      if (!selectedOp) {
        setError("Please select an employee.");
        return;
      }
      await checkInAttendance(selectedOp, undefined);
      setSelectedOp("");
      fetchRecords();
      setSuccessMsg("Shift started successfully.");
    } catch (err: any) {
      setError(err.message || "Failed to check in.");
    }
  };

  const handleCheckOut = async (record: AttendanceRecord) => {
    setError(null);
    setSuccessMsg(null);
    try {
      await checkOutAttendance(record.operator_id, undefined);
      fetchRecords();
      setSuccessMsg(`Shift ended for ${record.employee_name}.`);
    } catch (err: any) {
      setError(err.message || "Failed to check out.");
    }
  };

  const handleRecordWallProduction = async () => {
    setError(null);
    setSuccessMsg(null);
    if (!prodOp) {
      setError("Please select an operator to log completed walls.");
      return;
    }
    const qty = Number(prodQuantity);
    if (!Number.isInteger(qty) || qty <= 0) {
      setError("Wall quantity must be a positive whole integer greater than zero.");
      return;
    }
    setIsSubmittingProd(true);
    try {
      const res = await recordWallProduction({
        operator_id: prodOp,
        quantity: qty,
        job_id: prodJobId.trim() || undefined,
        notes: prodNotes.trim() || undefined,
      });
      setSuccessMsg(`Recorded ${qty} completed wall(s) for ${res.record.operator_name}.`);
      setProdQuantity(1);
      setProdNotes("");
      await fetchWallData();
    } catch (err: any) {
      setError(err.message || "Failed to record wall production.");
    } finally {
      setIsSubmittingProd(false);
    }
  };

  const handleOpenCorrection = (rec: WallProductionRecord) => {
    setCorrectingRecord(rec);
    setCorrectedQty(rec.quantity);
    setCorrectionReason("");
    setError(null);
    setSuccessMsg(null);
  };

  const handleSubmitCorrection = async () => {
    if (!correctingRecord) return;
    setError(null);
    setSuccessMsg(null);
    const qty = Number(correctedQty);
    if (!Number.isInteger(qty) || qty <= 0) {
      setError("Corrected quantity must be a positive integer greater than zero.");
      return;
    }
    setIsSubmittingCorrection(true);
    try {
      await correctWallProduction({
        record_id: correctingRecord.record_id,
        corrected_quantity: qty,
        reason: correctionReason.trim() || "Manual adjustment via dashboard",
      });
      setSuccessMsg(`Record ${correctingRecord.record_id} corrected to ${qty} walls. Total updated.`);
      setCorrectingRecord(null);
      await fetchWallData();
    } catch (err: any) {
      setError(err.message || "Failed to correct wall record.");
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  const formatTime = (ts: number | null) => {
    if (!ts) return "--";
    return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatDateTime = (ts: number | null) => {
    if (!ts) return "--";
    const d = new Date(ts * 1000);
    return `${d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  };

  return (
    <div className="panel card-attendance">
      <div className="att-header">
        <div className="att-header-left">
          <h2 className="att-title">
            <span>{activeTab === "attendance" ? "📋" : "🧱"}</span>
            <span>{activeTab === "attendance" ? "Employee Attendance" : "Wall Production Tracking"}</span>
          </h2>
          <span className="att-sqlite-badge">SQLITE RECORD</span>
        </div>

        {/* Tab Toggle */}
        <div className="att-tabs">
          <button
            type="button"
            onClick={() => setActiveTab("attendance")}
            className={`att-tab-btn ${activeTab === "attendance" ? "att-tab-btn-active-attendance" : ""}`}
          >
            📋 Shifts
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("production")}
            className={`att-tab-btn ${activeTab === "production" ? "att-tab-btn-active-production" : ""}`}
          >
            🧱 Walls ({wallTotals?.total_quantity ?? 0})
          </button>
        </div>
      </div>

      {/* Top Attendance Summary Metrics */}
      <div className="att-stats-grid">
        <div className="att-stat-card att-stat-card-active">
          <span className="att-stat-label">Active On Shift</span>
          <span className="att-stat-value att-val-active">
            {records.filter((r) => r.status === "ACTIVE").length}
          </span>
        </div>

        <div className="att-stat-card">
          <span className="att-stat-label">Present Today</span>
          <span className="att-stat-value att-val-present">
            {records.length}
          </span>
        </div>

        <div className="att-stat-card">
          <span className="att-stat-label">Completed</span>
          <span className="att-stat-value att-val-completed">
            {records.filter((r) => r.status === "COMPLETED").length}
          </span>
        </div>
      </div>

      {error && (
        <div className="att-alert att-alert-error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="att-alert att-alert-success">
          <span>✓</span>
          <span>{successMsg}</span>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 1: ATTENDANCE & SHIFTS                                     */}
      {/* ============================================================== */}
      {activeTab === "attendance" && (
        <div style={{ display: "flex", flexDirection: "column", flex: "1 1 auto" }}>
          {!isAdding ? (
            <div className="att-shift-controls">
              <label className="att-control-label">
                Select Operator
              </label>
              <div className="att-selector-row">
                <select
                  value={selectedOp}
                  onChange={handleSelectChange}
                  className="att-select"
                >
                  <option value="">-- Choose Operator --</option>
                  {operators.map((op) => (
                    <option key={op.operator_id} value={op.operator_id}>
                      {op.eid ? `${op.eid} — ${op.name}` : op.name} {op.employee_code ? `(${op.employee_code})` : ""}
                    </option>
                  ))}
                  <option disabled>-----------------</option>
                  <option value="ADD_NEW">+ Add New Employee</option>
                </select>

                <button
                  type="button"
                  onClick={handleCheckIn}
                  disabled={!selectedOp}
                  className="att-btn-start"
                >
                  START SHIFT
                </button>
              </div>
            </div>
          ) : (
            <div className="att-add-panel">
              <h4 className="att-add-header">
                REGISTER NEW EMPLOYEE
              </h4>

              <div className="att-eid-badge">
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>Employee ID (EID):</span>
                <span style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700, fontFamily: "monospace" }}>AUTO-GENERATED (K6K...)</span>
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  Full Name
                </label>
                <input
                  type="text"
                  value={newName}
                  placeholder="e.g. Anand Sharma"
                  onChange={(e) => setNewName(e.target.value)}
                  className="att-input"
                />
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  Employee Code (Optional)
                </label>
                <input
                  type="text"
                  value={newCode}
                  placeholder="e.g. OP-104"
                  onChange={(e) => setNewCode(e.target.value)}
                  className="att-input"
                />
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "var(--muted)", display: "block", marginBottom: "4px" }}>Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="att-input"
                >
                  <option value="operator">Operator</option>
                  <option value="technician">Technician</option>
                  <option value="supervisor">Supervisor</option>
                </select>
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                <button
                  type="button"
                  onClick={handleCancelAdd}
                  style={{
                    flex: 1,
                    padding: "7px 12px",
                    background: "#1e293b",
                    color: "#cbd5e1",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    cursor: "pointer",
                    borderRadius: "5px",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddEmployee}
                  style={{
                    flex: 1,
                    padding: "7px 12px",
                    background: "#16a34a",
                    color: "white",
                    border: "none",
                    cursor: "pointer",
                    borderRadius: "5px",
                    fontSize: "12px",
                    fontWeight: 700,
                  }}
                >
                  Add Employee
                </button>
              </div>
            </div>
          )}

          <div className="att-roster-section">
            <div className="att-roster-header">
              <h4 className="att-roster-title">
                Today's Attendance Roster
              </h4>
              <span className="att-roster-date">
                {new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}
              </span>
            </div>

            <div className="att-table-wrapper">
              <table className="att-table">
                <thead>
                  <tr>
                    <th>EID</th>
                    <th>Employee</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Worked</th>
                    <th>Overtime</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {records.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: "center", padding: "18px", color: "var(--muted)" }}>
                        No attendance records for today.
                      </td>
                    </tr>
                  ) : (
                    records.map((r) => (
                      <tr key={r.id}>
                        <td className="att-eid-cell">
                          {r.eid || "—"}
                        </td>
                        <td className="att-emp-name">{r.employee_name}</td>
                        <td className="att-time-cell">
                          {formatTime(r.shift_start)}
                        </td>
                        <td className="att-time-cell">
                          {formatTime(r.shift_end)}
                        </td>
                        <td style={{ fontVariantNumeric: "tabular-nums" }}>
                          <div style={{ fontWeight: 600, color: "#e6ecf3" }}>{r.worked_display || "0m"}</div>
                          {(r.overtime_seconds || 0) > 0 && (
                            <div style={{ fontSize: "10px", color: "#fbbf24", fontWeight: 600 }}>
                              +{r.overtime_display} OT
                            </div>
                          )}
                        </td>
                        <td
                          style={{
                            color: (r.overtime_seconds || 0) > 0 ? "#fbbf24" : "var(--muted)",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {r.overtime_display || "0m"}
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span
                              className={r.status === "ACTIVE" ? "att-badge-active" : "att-badge-completed"}
                            >
                              {r.status === "ACTIVE" ? "🟢 ACTIVE" : "COMPLETED"}
                            </span>
                            {r.status === "ACTIVE" && (
                              <button
                                type="button"
                                onClick={() => handleCheckOut(r)}
                                className="att-btn-end"
                                title="Clock out this operator"
                              >
                                END SHIFT
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: WALL PRODUCTION TRACKING                                */}
      {/* ============================================================== */}
      {activeTab === "production" && (
        <div>
          {/* Production Summary Metric Banner */}
          <div className="walls-summary-banner">
            <div className="walls-metric-card">
              <div className="walls-metric-header">
                <span className="walls-metric-label">Completed Walls</span>
                <div className="walls-scope-btns">
                  {(["today", "this_week", "all_time"] as const).map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setProdScope(s)}
                      className={`walls-scope-btn${prodScope === s ? " walls-scope-btn-active" : ""}`}
                    >
                      {s === "this_week" ? "Week" : s === "all_time" ? "All" : "Today"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="walls-metric-value">
                <span className="walls-metric-big">{wallTotals?.total_quantity ?? 0}</span>
                <span className="walls-metric-sub">
                  walls printed across {wallTotals?.record_count ?? 0} logs
                </span>
              </div>
            </div>

            {/* Operator distribution preview */}
            <div className="walls-dist-card">
              <span className="walls-dist-label">
                Operator Output ({prodScope.replace("_", " ")})
              </span>
              <div className="walls-dist-tags">
                {wallTotals?.by_operator && wallTotals.by_operator.length > 0 ? (
                  wallTotals.by_operator.map((op) => (
                    <span key={op.operator_id} className="walls-op-tag">
                      <strong>{op.operator_name}:</strong> {op.total_quantity}
                    </span>
                  ))
                ) : (
                  <span className="walls-op-tag-empty">
                    No walls recorded for this period yet.
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Quick Record Form */}
          <div className="walls-log-form">
            <h4 className="walls-form-title">Log Completed Wall Units</h4>
            <div className="walls-form-grid">
              <div className="walls-form-field">
                <label className="walls-form-label">Operator</label>
                <select
                  className="walls-form-select"
                  value={prodOp}
                  onChange={(e) => setProdOp(e.target.value)}
                >
                  <option value="">-- Choose Operator --</option>
                  {operators.map((op) => (
                    <option key={op.operator_id} value={op.name}>
                      {op.eid ? `${op.eid} — ${op.name}` : op.name}{" "}
                      {op.employee_code ? `(${op.employee_code})` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="walls-form-field">
                <label className="walls-form-label">Walls Completed</label>
                <input
                  className="walls-form-input"
                  type="number"
                  min="1"
                  step="1"
                  value={prodQuantity}
                  onChange={(e) => setProdQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
                />
              </div>

              <div className="walls-form-field">
                <label className="walls-form-label">Job ID (Optional)</label>
                <input
                  className="walls-form-input"
                  type="text"
                  placeholder="e.g. WALL-JOB-01"
                  value={prodJobId}
                  onChange={(e) => setProdJobId(e.target.value)}
                />
              </div>

              <div className="walls-form-field">
                <label className="walls-form-label">Notes (Optional)</label>
                <input
                  className="walls-form-input"
                  type="text"
                  placeholder="e.g. Standard 3m wall section"
                  value={prodNotes}
                  onChange={(e) => setProdNotes(e.target.value)}
                />
              </div>
            </div>

            <div className="walls-form-footer">
              <button
                type="button"
                className="walls-btn-log"
                onClick={handleRecordWallProduction}
                disabled={!prodOp || isSubmittingProd}
              >
                <span>🧱</span>
                <span>{isSubmittingProd ? "Logging..." : "Log Completed Walls"}</span>
              </button>
            </div>
          </div>

          {/* Wall Production Records Table */}
          <div>
            <div className="walls-log-header">
              <h4 className="walls-log-title">
                Wall Production Log ({prodScope.replace("_", " ")})
              </h4>
              <button type="button" className="walls-refresh-btn" onClick={fetchWallData}>
                🔄 Refresh
              </button>
            </div>

            <div className="att-table-wrapper">
              <table className="att-table">
                <thead>
                  <tr>
                    <th>Record ID</th>
                    <th>Operator</th>
                    <th>Quantity</th>
                    <th>Logged At</th>
                    <th>Job / Shift</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {wallRecords.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: "center", padding: "14px", color: "var(--muted)" }}>
                        No wall production records found for this period.
                      </td>
                    </tr>
                  ) : (
                    wallRecords.map((r) => (
                      <tr key={r.record_id}>
                        <td className="att-eid-cell">{r.record_id}</td>
                        <td className="att-emp-name">
                          {r.operator_name}{r.employee_code ? ` (${r.employee_code})` : ""}
                        </td>
                        <td>
                          <span className="walls-qty-badge">
                            {r.quantity} {r.quantity === 1 ? "wall" : "walls"}
                          </span>
                        </td>
                        <td className="att-time-cell">{formatDateTime(r.created_at)}</td>
                        <td className="att-time-cell">
                          {r.job_id || "Standard"}{r.shift_id ? ` (Shift #${r.shift_id})` : ""}
                          {r.notes ? ` • ${r.notes}` : ""}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="walls-btn-correct"
                            onClick={() => handleOpenCorrection(r)}
                            title="Correct this wall entry"
                          >
                            ✏️ Correct
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Audit Correction Modal */}
          {correctingRecord && (
            <div className="modal-overlay" onClick={() => setCorrectingRecord(null)}>
              <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h3 className="modal-title">
                    <span>✏️</span>
                    <span>Audit Correction for {correctingRecord.record_id}</span>
                  </h3>
                  <button
                    type="button"
                    className="modal-close-btn"
                    onClick={() => setCorrectingRecord(null)}
                  >
                    ✕
                  </button>
                </div>

                <div className="modal-info-block">
                  <div><strong>Operator:</strong> {correctingRecord.operator_name}</div>
                  <div><strong>Original Logged Count:</strong> {correctingRecord.quantity} walls</div>
                  <div><strong>Original Date:</strong> {formatDateTime(correctingRecord.created_at)}</div>
                </div>

                <div className="modal-field">
                  <label className="modal-field-label">
                    New Corrected Quantity (Positive Integer)
                  </label>
                  <input
                    className="modal-field-input"
                    type="number"
                    min="1"
                    step="1"
                    value={correctedQty}
                    onChange={(e) => setCorrectedQty(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  />
                </div>

                <div className="modal-field" style={{ marginBottom: "16px" }}>
                  <label className="modal-field-label">
                    Reason for Correction (Audit Log)
                  </label>
                  <input
                    className="modal-field-input"
                    type="text"
                    placeholder="e.g. Recounted by supervisor; 1 wall was incomplete"
                    value={correctionReason}
                    onChange={(e) => setCorrectionReason(e.target.value)}
                  />
                </div>

                <p className="modal-compliance-note">
                  🔒 Audit Compliance: The original record will be marked corrected and preserved in the
                  audit trail. Totals will accurately reflect the new count without duplicate inflation.
                </p>

                <div className="modal-actions">
                  <button
                    type="button"
                    className="modal-btn-cancel"
                    onClick={() => setCorrectingRecord(null)}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="modal-btn-save"
                    onClick={handleSubmitCorrection}
                    disabled={isSubmittingCorrection}
                  >
                    {isSubmittingCorrection ? "Saving..." : "Save Correction"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
