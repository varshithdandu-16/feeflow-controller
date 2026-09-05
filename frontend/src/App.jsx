import { useEffect, useMemo, useState } from "react";
import "./App.css";

import {
  checkHealth,
  runAgent,
  getLatestAgentRun,
  getReviewCases,
  submitReviewDecision,
  verifyTransaction,
  getAuditRecords,
} from "./api";

const FILTERS = [
  "ALL",
  "CLEAR",
  "MONITOR",
  "HUMAN_REVIEW",
  "BLOCKED",
];

const DECISIONS = [
  "CONFIRM_REVIEW",
  "ESCALATE",
  "REQUEST_MORE_EVIDENCE",
];

function normalizeStatus(value) {
  const status = String(value || "UNKNOWN").toUpperCase();

  if (status === "AUTO_CLEAR") return "CLEAR";
  if (status === "BLOCK") return "BLOCKED";
  return status;
}

function pretty(value) {
  return String(value || "—")
    .replaceAll("_", " ")
    .toUpperCase();
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString();
}

function formatMoney(value, currency = "INR") {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const amount = Number(value);

  if (Number.isNaN(amount)) {
    return String(value);
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

function StatusBadge({ status }) {
  const normalized = normalizeStatus(status);

  return (
    <span
      className={`status-badge ${normalized
        .toLowerCase()
        .replaceAll("_", "-")}`}
    >
      {pretty(normalized)}
    </span>
  );
}

function App() {
  const [activeView, setActiveView] =
    useState("overview");

  const [statusFilter, setStatusFilter] =
    useState("ALL");

  const [agentData, setAgentData] =
    useState(null);

  const [reviewCases, setReviewCases] =
    useState([]);

  const [auditRecords, setAuditRecords] =
    useState([]);

  const [selectedCase, setSelectedCase] =
    useState(null);

  const [verificationData, setVerificationData] =
    useState(null);

  const [backendStatus, setBackendStatus] =
    useState("Checking backend...");

  const [isRunning, setIsRunning] =
    useState(false);

  const [
    isLoadingReviews,
    setIsLoadingReviews,
  ] = useState(false);

  const [
    isLoadingAudit,
    setIsLoadingAudit,
  ] = useState(false);

  const [isVerifying, setIsVerifying] =
    useState(false);

  const [
    isSubmittingDecision,
    setIsSubmittingDecision,
  ] = useState(false);

  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] =
    useState("");

  const [decision, setDecision] =
    useState("");

  const [decisionReason, setDecisionReason] =
    useState("");

  const [reviewer, setReviewer] =
    useState("Horizon Risk Team");

  useEffect(() => {
    async function bootstrap() {
      try {
        await checkHealth();
        setBackendStatus("Backend ready");
      } catch {
        setBackendStatus(
          "Backend unavailable",
        );
      }

      try {
        const latest =
          await getLatestAgentRun();

        if (latest?.run) {
          setAgentData(latest.run);
        }
      } catch {
        // No previous run is acceptable.
      }

      try {
        await refreshReviews();
      } catch {
        setReviewCases([]);
      }

      try {
        await refreshAudit();
      } catch {
        setAuditRecords([]);
      }
    }

    bootstrap();
  }, []);

  async function refreshReviews() {
    setIsLoadingReviews(true);

    try {
      const data =
        await getReviewCases();

      const cases = Array.isArray(data)
        ? data
        : data?.cases ||
          data?.review_cases ||
          [];

      setReviewCases(cases);

      return cases;
    } finally {
      setIsLoadingReviews(false);
    }
  }

  async function refreshAudit() {
    setIsLoadingAudit(true);

    try {
      const data =
        await getAuditRecords();

      const records = Array.isArray(data)
        ? data
        : data?.records || [];

      setAuditRecords(records);

      return records;
    } finally {
      setIsLoadingAudit(false);
    }
  }

  const summary = agentData?.summary || {
    clear: 0,
    monitor: 0,
    human_review: 0,
    blocked: 0,
  };

  const casesProcessed =
    agentData?.cases_processed || 0;

  const assessments =
    agentData?.assessments || [];

  const investigations =
    agentData?.investigations || [];

  const openReviewCount =
    reviewCases.filter(
      (item) =>
        String(
          item?.status || "",
        ).toUpperCase() === "OPEN",
    ).length;

  const allCases = useMemo(() => {
    return assessments.map(
      (assessment) => {
        const investigation =
          investigations.find(
            (item) =>
              item.case_id ===
              assessment.case_id,
          );

        const review =
          reviewCases.find(
            (item) =>
              item.case_id ===
              assessment.case_id,
          );

        return {
          case_id:
            assessment.case_id,

          status:
            normalizeStatus(
              assessment.action,
            ),

          action:
            assessment.action,

          requires_human:
            assessment.requires_human,

          reason:
            investigation?.explanation ||
            investigation?.finding ||
            review?.explanation ||
            review?.finding ||
            assessment.reason ||
            "No explanation available.",

          finding:
            investigation?.finding ||
            review?.finding ||
            null,

          explanation:
            investigation?.explanation ||
            review?.explanation ||
            null,

          risk:
            investigation?.risk ||
            review?.risk ||
            null,

          evidence:
            investigation?.evidence ||
            review?.evidence ||
            null,

          recommendation:
            investigation?.recommendation ||
            review?.recommendation ||
            null,

          confidence:
            investigation?.confidence ||
            review?.confidence ||
            null,
        };
      },
    );
  }, [
    assessments,
    investigations,
    reviewCases,
  ]);

  const filteredCases = useMemo(() => {
    if (statusFilter === "ALL") {
      return allCases;
    }

    return allCases.filter(
      (item) =>
        normalizeStatus(item.status) ===
        statusFilter,
    );
  }, [
    allCases,
    statusFilter,
  ]);

  const selectedId =
    selectedCase?.case_id || null;

  const selectedAssessment =
    selectedId
      ? assessments.find(
          (item) =>
            item.case_id === selectedId,
        )
      : null;

  const selectedInvestigation =
    selectedId
      ? investigations.find(
          (item) =>
            item.case_id === selectedId,
        )
      : null;

  const selectedReview =
    selectedId
      ? reviewCases.find(
          (item) =>
            item.case_id === selectedId,
        )
      : null;

  const selectedEvidence =
    selectedInvestigation?.evidence ||
    selectedReview?.evidence ||
    verificationData
      ?.reconciliation
      ?.evidence ||
    null;

  const expectedAmount =
    verificationData
      ?.reconciliation
      ?.evidence
      ?.expected_amount ??
    selectedEvidence
      ?.expected_amount;

  const observedAmount =
    verificationData
      ?.reconciliation
      ?.evidence
      ?.observed_amount ??
    selectedEvidence
      ?.observed_amount;

  const difference =
    verificationData
      ?.reconciliation
      ?.evidence
      ?.difference ??
    selectedEvidence?.difference;

  const currency =
    selectedEvidence?.currency ||
    "INR";

  const caseHistory = useMemo(() => {
    if (!selectedId) {
      return [];
    }

    return auditRecords
      .filter(
        (record) =>
          record?.case_id === selectedId,
      )
      .sort((a, b) => {
        const aTime =
          new Date(
            a?.timestamp || 0,
          ).getTime();

        const bTime =
          new Date(
            b?.timestamp || 0,
          ).getTime();

        return bTime - aTime;
      });
  }, [
    auditRecords,
    selectedId,
  ]);

  async function openCase(item) {
    setSelectedCase(item);
    setVerificationData(null);
    setDecision("");
    setDecisionReason("");
    setError("");
    setSuccessMessage("");

    setIsVerifying(true);

    try {
      const result =
        await verifyTransaction(
          item.case_id,
        );

      setVerificationData(result);
    } catch (err) {
      setError(
        err.message ||
          "Unable to verify transaction.",
      );
    } finally {
      setIsVerifying(false);
    }
  }

  function closeCase() {
    setSelectedCase(null);
    setVerificationData(null);
    setDecision("");
    setDecisionReason("");
  }

  function goOverview() {
    setActiveView("overview");
    setStatusFilter("ALL");
    closeCase();
    setError("");
    setSuccessMessage("");
  }

  function goControls(filter = "ALL") {
    setActiveView("controls");
    setStatusFilter(filter);
    closeCase();
    setError("");
    setSuccessMessage("");
  }

  async function goReviews() {
    setActiveView("reviews");
    setStatusFilter("ALL");
    setError("");

    try {
      await refreshReviews();
    } catch (err) {
      setError(
        err.message ||
          "Unable to load review queue.",
      );
    }
  }

  async function goAudit() {
    setActiveView("audit");
    setStatusFilter("ALL");
    setError("");

    try {
      await refreshAudit();
    } catch (err) {
      setError(
        err.message ||
          "Unable to load audit trail.",
      );
    }
  }

  async function handleRunAgent() {
    setIsRunning(true);
    setError("");
    setSuccessMessage("");

    try {
      const result =
        await runAgent();

      setAgentData(result);

      await Promise.all([
        refreshReviews(),
        refreshAudit(),
      ]);

      setActiveView("overview");
      setStatusFilter("ALL");

      setSuccessMessage(
        `Agent completed — ${
          result.cases_processed || 0
        } financial cases evaluated.`,
      );
    } catch (err) {
      setError(
        err.message ||
          "Agent execution failed.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  async function handleDecision() {
    if (!selectedCase) {
      return;
    }

    if (!DECISIONS.includes(decision)) {
      setError(
        "Select a valid human-review decision.",
      );
      return;
    }

    if (!decisionReason.trim()) {
      setError(
        "A decision reason is required.",
      );
      return;
    }

    if (!reviewer.trim()) {
      setError(
        "Reviewer identity is required.",
      );
      return;
    }

    setIsSubmittingDecision(true);
    setError("");
    setSuccessMessage("");

    try {
      const caseId =
        selectedCase.case_id;

      await submitReviewDecision(
        caseId,
        decision,
        decisionReason.trim(),
        reviewer.trim(),
      );

      await Promise.all([
        refreshReviews(),
        refreshAudit(),
      ]);

      setSelectedCase(null);
      setVerificationData(null);
      setDecision("");
      setDecisionReason("");

      setSuccessMessage(
        `${caseId} decision recorded in the server-side audit trail.`,
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to record human-review decision.",
      );
    } finally {
      setIsSubmittingDecision(
        false,
      );
    }
  }

  const currentSelectedStatus =
    selectedReview?.status ||
    selectedCase?.status ||
    normalizeStatus(
      selectedAssessment?.action,
    );

  const selectedRisk =
    selectedCase?.risk ||
    selectedInvestigation?.risk ||
    selectedReview?.risk ||
    verificationData?.risk ||
    "NOT AVAILABLE";

  const failureType =
    verificationData
      ?.reconciliation
      ?.discrepancy_type ||
    selectedEvidence
      ?.discrepancy_type ||
    verificationData
      ?.control
      ?.exception_code ||
    "NOT SPECIFIED";

  const reconciliationStatus =
    verificationData
      ?.reconciliation
      ?.status ||
    "NOT VERIFIED";

  const reconciliationMessage =
    verificationData
      ?.reconciliation
      ?.message ||
    "No reconciliation message available.";

  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            F
          </div>

          <div>
            <div className="brand-name">
              FeeFlow
            </div>

            <div className="brand-subtitle">
              Controller
            </div>
          </div>

        </div>

        <nav className="navigation">

          <button
            className={`nav-item ${
              activeView ===
              "overview"
                ? "active"
                : ""
            }`}
            onClick={goOverview}
          >
            <span>◈</span>
            Overview
          </button>

          <button
            className={`nav-item ${
              activeView ===
              "controls"
                ? "active"
                : ""
            }`}
            onClick={() =>
              goControls("ALL")
            }
          >
            <span>✓</span>
            Controls
          </button>

          <button
            className={`nav-item ${
              activeView ===
              "reviews"
                ? "active"
                : ""
            }`}
            onClick={goReviews}
          >
            <span>!</span>
            Human Review

            {openReviewCount >
              0 && (
              <span className="nav-count">
                {openReviewCount}
              </span>
            )}

          </button>

          <button
            className={`nav-item ${
              activeView ===
              "audit"
                ? "active"
                : ""
            }`}
            onClick={goAudit}
          >
            <span>▤</span>
            Audit Trail
          </button>

        </nav>

        <div className="sidebar-footer">

          <div className="system-status">

            <span className="status-dot" />

            <div>

              <strong>
                {backendStatus ===
                "Backend ready"
                  ? "System operational"
                  : backendStatus}
              </strong>

              <small>
                {backendStatus ===
                "Backend ready"
                  ? "Control engine online"
                  : "Control engine unavailable"}
              </small>

            </div>

          </div>

          <div className="version">
            FeeFlow Controller · v0.1.0
          </div>

        </div>

      </aside>

      {/* MAIN */}

      <main className="main-content">

        <header className="topbar">

          <div>

            <div className="eyebrow">
              FINANCIAL CONTROL CENTER
            </div>

            <h1>
              Payment Risk Overview
            </h1>

            <p>
              Deterministic financial
              controls with autonomous
              investigation and human
              oversight.
            </p>

          </div>

          <div className="topbar-actions">

            <div className="live-indicator">
              <span className="status-dot" />
              {backendStatus}
            </div>

            <button
              className="run-button"
              disabled={isRunning}
              onClick={
                handleRunAgent
              }
            >
              {isRunning
                ? "Running Agent..."
                : "Run Agent"}

              <span>→</span>
            </button>

          </div>

        </header>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="success-message">
            {successMessage}
          </div>
        )}

        {/* OVERVIEW */}

        {activeView ===
          "overview" && (
          <>

            <section className="metrics-grid">

              <button
                className="metric-card metric-card-button"
                onClick={() =>
                  goControls("ALL")
                }
              >

                <div className="metric-label">
                  CASES PROCESSED
                </div>

                <div className="metric-value">
                  {agentData
                    ? casesProcessed
                    : "—"}
                </div>

                <div className="metric-meta">
                  <span className="positive">
                    {agentData
                      ? "Live"
                      : "Ready"}
                  </span>

                  Evaluated financial
                  cases
                </div>

              </button>

              <button
                className="metric-card success metric-card-button"
                onClick={() =>
                  goControls("CLEAR")
                }
              >

                <div className="metric-label">
                  AUTO CLEARED
                </div>

                <div className="metric-value">
                  {agentData
                    ? summary.clear
                    : "—"}
                </div>

                <div className="metric-meta">

                  <span className="positive">
                    {agentData &&
                    casesProcessed
                      ? `${(
                          (summary.clear /
                            casesProcessed) *
                          100
                        ).toFixed(1)}%`
                      : "—"}
                  </span>

                  Passed controls
                  automatically

                </div>

              </button>

              <button
                className="metric-card warning metric-card-button"
                onClick={goReviews}
              >

                <div className="metric-label">
                  HUMAN REVIEW
                </div>

                <div className="metric-value">
                  {agentData
                    ? openReviewCount
                    : "—"}
                </div>

                <div className="metric-meta">

                  <span className="warning-text">
                    {openReviewCount >
                    0
                      ? "Attention"
                      : "Clear"}
                  </span>

                  Open cases awaiting
                  review

                </div>

              </button>

              <button
                className="metric-card critical metric-card-button"
                onClick={() =>
                  goControls("BLOCKED")
                }
              >

                <div className="metric-label">
                  BLOCKED
                </div>

                <div className="metric-value">
                  {agentData
                    ? summary.blocked
                    : "—"}
                </div>

                <div className="metric-meta">

                  <span className="warning-text">
                    {agentData &&
                    casesProcessed
                      ? `${(
                          (summary.blocked /
                            casesProcessed) *
                          100
                        ).toFixed(1)}%`
                      : "—"}
                  </span>

                  Stopped by control
                  policy

                </div>

              </button>

            </section>

            <section className="dashboard-grid">

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <h2>
                      Agent Assessments
                    </h2>

                    <p>
                      Latest financial
                      control outcomes
                    </p>

                  </div>

                  <button
                    className="text-button"
                    onClick={() =>
                      goControls("ALL")
                    }
                  >
                    View all →
                  </button>

                </div>

                <div className="table-wrapper">

                  <table>

                    <thead>

                      <tr>
                        <th>CASE</th>
                        <th>STATUS</th>
                        <th>RISK</th>
                        <th>WHY</th>
                      </tr>

                    </thead>

                    <tbody>

                      {allCases
                        .slice(0, 8)
                        .map(
                          (item) => (
                            <tr
                              key={
                                item.case_id
                              }
                              onClick={() =>
                                openCase(
                                  item,
                                )
                              }
                            >

                              <td>
                                <strong>
                                  {
                                    item.case_id
                                  }
                                </strong>
                              </td>

                              <td>
                                <StatusBadge
                                  status={
                                    item.status
                                  }
                                />
                              </td>

                              <td>
                                {item.risk ||
                                  "—"}
                              </td>

                              <td>
                                {
                                  item.reason
                                }
                              </td>

                            </tr>
                          ),
                        )}

                      {!agentData && (
                        <tr>
                          <td colSpan="4">
                            Run the agent
                            to begin
                            evaluation.
                          </td>
                        </tr>
                      )}

                    </tbody>

                  </table>

                </div>

              </div>

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <h2>
                      Control Pipeline
                    </h2>

                    <p>
                      Current operational
                      posture
                    </p>

                  </div>

                </div>

                <div className="pipeline">

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon clear">
                        ✓
                      </span>

                      <div>

                        <strong>
                          Auto Clear
                        </strong>

                        <small>
                          Controls passed
                        </small>

                      </div>

                    </div>

                    <strong>
                      {agentData
                        ? summary.clear
                        : "—"}
                    </strong>

                  </div>

                  <div className="progress-track">

                    <div
                      className="progress-fill"
                      style={{
                        width: `${
                          agentData &&
                          casesProcessed
                            ? (
                                (summary.clear /
                                  casesProcessed) *
                                100
                              )
                            : 0
                        }%`,
                      }}
                    />

                  </div>

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon review">
                        !
                      </span>

                      <div>

                        <strong>
                          Human Review
                        </strong>

                        <small>
                          Open exceptions
                        </small>

                      </div>

                    </div>

                    <strong>
                      {agentData
                        ? openReviewCount
                        : "—"}
                    </strong>

                  </div>

                  <div className="progress-track">

                    <div
                      className="progress-fill review-fill"
                      style={{
                        width: `${
                          agentData &&
                          casesProcessed
                            ? (
                                (summary.human_review /
                                  casesProcessed) *
                                100
                              )
                            : 0
                        }%`,
                      }}
                    />

                  </div>

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon blocked">
                        ×
                      </span>

                      <div>

                        <strong>
                          Blocked
                        </strong>

                        <small>
                          Policy-stopped
                          cases
                        </small>

                      </div>

                    </div>

                    <strong>
                      {agentData
                        ? summary.blocked
                        : "—"}
                    </strong>

                  </div>

                </div>

                <div className="agent-card">

                  <div className="agent-icon">
                    ✦
                  </div>

                  <div>

                    <strong>
                      Agent control posture
                    </strong>

                    <p>
                      Deterministic controls
                      remain authoritative.
                      The agent investigates
                      exceptions and routes
                      them to the appropriate
                      workflow.
                    </p>

                  </div>

                </div>

              </div>

            </section>

          </>
        )}

        {/* CONTROLS */}

        {activeView ===
          "controls" && (
          <section className="panel page-panel">

            <div className="panel-header">

              <div>

                <div className="eyebrow">
                  CONTROL WORKBENCH
                </div>

                <h2>
                  Financial Control
                  Assessments
                </h2>

                <p>
                  Filter by outcome and
                  select any case for full
                  verification evidence.
                </p>

              </div>

              <div className="review-header-actions">

                <button
                  className="text-button"
                  onClick={
                    goOverview
                  }
                >
                  ← Overview
                </button>

                <button
                  className="run-button"
                  disabled={isRunning}
                  onClick={
                    handleRunAgent
                  }
                >
                  {isRunning
                    ? "Running..."
                    : "Run Agent"}
                </button>

              </div>

            </div>

            <div className="filter-row">

              {FILTERS.map(
                (filter) => (
                  <button
                    key={filter}
                    className={`filter-button ${
                      statusFilter ===
                      filter
                        ? "active"
                        : ""
                    }`}
                    onClick={() =>
                      setStatusFilter(
                        filter,
                      )
                    }
                  >
                    {pretty(filter)}
                  </button>
                ),
              )}

            </div>

            <div className="table-wrapper">

              <table>

                <thead>

                  <tr>
                    <th>CASE</th>
                    <th>STATUS</th>
                    <th>RISK</th>
                    <th>HUMAN</th>
                    <th>EXCEPTION</th>
                  </tr>

                </thead>

                <tbody>

                  {filteredCases.map(
                    (item) => (
                      <tr
                        key={item.case_id}
                        onClick={() =>
                          openCase(
                            item,
                          )
                        }
                      >

                        <td>
                          <strong>
                            {
                              item.case_id
                            }
                          </strong>
                        </td>

                        <td>
                          <StatusBadge
                            status={
                              item.status
                            }
                          />
                        </td>

                        <td>
                          {item.risk ||
                            "—"}
                        </td>

                        <td>
                          {item.requires_human
                            ? "YES"
                            : "NO"}
                        </td>

                        <td>
                          {item.reason}
                        </td>

                      </tr>
                    ),
                  )}

                  {filteredCases.length ===
                    0 && (
                    <tr>
                      <td colSpan="5">
                        No cases match the
                        selected filter.
                      </td>
                    </tr>
                  )}

                </tbody>

              </table>

            </div>

          </section>
        )}

        {/* HUMAN REVIEW */}

        {activeView ===
          "reviews" && (
          <section className="panel page-panel">

            <div className="panel-header">

              <div>

                <div className="eyebrow">
                  REVIEW OPERATIONS
                </div>

                <h2>
                  Human Review Queue
                </h2>

                <p>
                  Active cases requiring a
                  human workflow decision.
                </p>

              </div>

              <div className="review-header-actions">

                <button
                  className="text-button"
                  onClick={
                    goOverview
                  }
                >
                  ← Overview
                </button>

                <button
                  className="review-button"
                  disabled={
                    isLoadingReviews
                  }
                  onClick={
                    refreshReviews
                  }
                >
                  {isLoadingReviews
                    ? "Refreshing..."
                    : "Refresh Queue"}
                </button>

              </div>

            </div>

            <div className="review-summary">

              <div className="review-summary-number">
                {openReviewCount}
              </div>

              <div>

                <strong>
                  Open review cases
                </strong>

                <p>
                  Resolved cases leave
                  this active queue but
                  remain in server-side
                  audit history.
                </p>

              </div>

              <div className="review-rule">

                <span className="status-dot warning-dot" />

                Human action required

              </div>

            </div>

            {reviewCases.length ===
            0 ? (
              <div className="empty-state">
                No open review cases
                currently available.
              </div>
            ) : (
              <div className="review-list">

                {reviewCases.map(
                  (item) => (
                    <button
                      key={item.case_id}
                      className="review-item"
                      onClick={() =>
                        openCase(item)
                      }
                    >

                      <div>

                        <strong>
                          {
                            item.case_id
                          }
                        </strong>

                        <p>
                          {item.finding ||
                            item.explanation ||
                            "Financial exception requires review."}
                        </p>

                      </div>

                      <StatusBadge
                        status={
                          item.status
                        }
                      />

                    </button>
                  ),
                )}

              </div>
            )}

          </section>
        )}

        {/* AUDIT */}

        {activeView ===
          "audit" && (
          <section className="panel page-panel">

            <div className="panel-header">

              <div>

                <div className="eyebrow">
                  CONTROL EVIDENCE
                </div>

                <h2>
                  Audit Trail
                </h2>

                <p>
                  Persisted control and human
                  workflow events, newest first.
                </p>

              </div>

              <div className="review-header-actions">

                <button
                  className="text-button"
                  onClick={
                    goOverview
                  }
                >
                  ← Overview
                </button>

                <button
                  className="review-button"
                  disabled={
                    isLoadingAudit
                  }
                  onClick={
                    refreshAudit
                  }
                >
                  {isLoadingAudit
                    ? "Refreshing..."
                    : "Refresh Audit"}
                </button>

              </div>

            </div>

            <div className="audit-callout">

              <strong>
                Where is a decision stored?
              </strong>

              <p>
                Agent control events and
                human-review decisions are
                persisted by the server-side
                FeeFlow run store. A human
                decision is recorded as a
                separate audit event with the
                case ID, reviewer, decision,
                reason and timestamp. The
                underlying financial transaction
                is not modified.
              </p>

            </div>

            <div className="audit-stat-grid">

              <div className="audit-stat">

                <span>
                  TOTAL EVENTS
                </span>

                <strong>
                  {auditRecords.length}
                </strong>

              </div>

              <div className="audit-stat">

                <span>
                  RECENT EVENTS
                </span>

                <strong>
                  {Math.min(
                    8,
                    auditRecords.length,
                  )}
                </strong>

              </div>

              <div className="audit-stat">

                <span>
                  HUMAN DECISIONS
                </span>

                <strong>
                  {
                    auditRecords.filter(
                      (record) =>
                        record?.event ===
                        "HUMAN_REVIEW_DECISION",
                    ).length
                  }
                </strong>

              </div>

              <div className="audit-stat">

                <span>
                  STORAGE
                </span>

                <strong>
                  Server-side Run Store
                </strong>

              </div>

            </div>

            <div className="panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Recent Audit Activity
                  </h2>

                  <p>
                    Newest persisted events
                    first
                  </p>

                </div>

              </div>

              <div className="table-wrapper">

                <table>

                  <thead>

                    <tr>
                      <th>TIME</th>
                      <th>CASE</th>
                      <th>EVENT</th>
                      <th>ACTION</th>
                      <th>DETAIL</th>
                    </tr>

                  </thead>

                  <tbody>

                    {auditRecords
                      .slice(0, 8)
                      .map(
                        (
                          record,
                          index,
                        ) => (
                          <tr
                            key={`${record?.case_id || "audit"}-${record?.timestamp || index}-${index}`}
                          >

                            <td>
                              {formatDate(
                                record?.timestamp,
                              )}
                            </td>

                            <td>
                              <strong>
                                {record?.case_id ||
                                  "—"}
                              </strong>
                            </td>

                            <td>
                              {pretty(
                                record?.event ||
                                  "CONTROL_ASSESSMENT",
                              )}
                            </td>

                            <td>
                              {pretty(
                                record?.decision ||
                                  record?.agent_action ||
                                  record?.control_action ||
                                  "RECORDED",
                              )}
                            </td>

                            <td>
                              {record?.reason ||
                                record?.message ||
                                "Audit event recorded."}
                            </td>

                          </tr>
                        ),
                      )}

                    {auditRecords.length ===
                      0 && (
                      <tr>
                        <td colSpan="5">
                          No audit events
                          available.
                        </td>
                      </tr>
                    )}

                  </tbody>

                </table>

              </div>

            </div>

          </section>
        )}

        {/* CASE MODAL */}

        {selectedCase && (
          <div
            className="case-overlay"
            onClick={closeCase}
          >

            <div
              className="case-modal"
              onClick={(event) =>
                event.stopPropagation()
              }
            >

              <div className="modal-header">

                <div>

                  <div className="eyebrow">
                    FINANCIAL CASE
                  </div>

                  <h2>
                    {selectedCase.case_id}
                  </h2>

                  <p>
                    Deterministic verification,
                    reconciliation and review
                    history.
                  </p>

                </div>

                <button
                  className="close-button"
                  onClick={closeCase}
                >
                  ×
                </button>

              </div>

              <div className="case-details">

                <div>
                  <span>
                    STATUS
                  </span>

                  <strong>
                    <StatusBadge
                      status={
                        currentSelectedStatus
                      }
                    />
                  </strong>
                </div>

                <div>
                  <span>
                    RISK
                  </span>

                  <strong>
                    {selectedRisk}
                  </strong>
                </div>

                <div>
                  <span>
                    HUMAN REQUIRED
                  </span>

                  <strong>
                    {selectedCase.requires_human
                      ? "YES"
                      : "NO"}
                  </strong>
                </div>

                <div>
                  <span>
                    CONFIDENCE
                  </span>

                  <strong>
                    {selectedCase.confidence !=
                    null
                      ? `${(
                          selectedCase.confidence *
                          100
                        ).toFixed(0)}%`
                      : "—"}
                  </strong>
                </div>

              </div>

              {isVerifying && (
                <div className="evidence-box">

                  <span>
                    LIVE VERIFICATION
                  </span>

                  <p>
                    Rechecking the financial
                    control path for this
                    case...
                  </p>

                </div>
              )}

              <div className="evidence-box">

                <span>
                  WHAT HAPPENED
                </span>

                <p>
                  {selectedInvestigation?.finding ||
                    selectedReview?.finding ||
                    selectedCase.reason}
                </p>

                <p>
                  {selectedInvestigation?.explanation ||
                    selectedReview?.explanation ||
                    selectedCase.reason}
                </p>

              </div>

              <div className="evidence-box">

                <span>
                  WHERE THE CONTROL FAILED
                </span>

                <div className="pipeline">

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon clear">
                        1
                      </span>

                      <div>

                        <strong>
                          Fee Ledger → Gateway
                        </strong>

                        <small>
                          Expected amount versus
                          gateway observation
                        </small>

                      </div>

                    </div>

                    <strong>
                      {selectedEvidence
                        ?.failed_stage ===
                      "FEE_LEDGER_TO_PAYMENT_GATEWAY"
                        ? "EXCEPTION"
                        : "PASS"}
                    </strong>

                  </div>

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon review">
                        2
                      </span>

                      <div>

                        <strong>
                          Gateway → Settlement
                        </strong>

                        <small>
                          Transaction identity and
                          settlement consistency
                        </small>

                      </div>

                    </div>

                    <strong>
                      {selectedEvidence
                          ?.failed_stage ===
                        "EXPECTED_AMOUNT_TO_SETTLEMENT" ||
                      selectedEvidence
                          ?.failed_stage ===
                        "PAYMENT_GATEWAY_TO_SETTLEMENT" ||
                      selectedEvidence
                          ?.failed_stage ===
                        "PAYMENT_GATEWAY_TO_SETTLEMENT_IDENTITY"
                        ? "EXCEPTION"
                        : "PASS"}
                    </strong>

                  </div>

                  <div className="pipeline-row">

                    <div className="pipeline-title">

                      <span className="pipeline-icon blocked">
                        3
                      </span>

                      <div>

                        <strong>
                          Settlement → Bank
                        </strong>

                        <small>
                          Settlement identity,
                          amount and reference
                        </small>

                      </div>

                    </div>

                    <strong>
                      {selectedEvidence
                        ?.failed_stage?.startsWith(
                          "SETTLEMENT_TO_BANK",
                        ) ||
                      selectedEvidence
                        ?.failed_stage ===
                        "BANK_REFERENCE_UNIQUENESS" ||
                      selectedEvidence
                        ?.failed_stage ===
                        "SETTLEMENT_TO_BANK_IDENTITY" ||
                      selectedEvidence
                        ?.failed_stage ===
                        "SETTLEMENT_TO_BANK_AMOUNT"
                        ? "EXCEPTION"
                        : "PASS"}
                    </strong>

                  </div>

                </div>

                <p>
                  <strong>
                    Failure type:
                  </strong>{" "}
                  {failureType}
                </p>

                <p>
                  <strong>
                    Reconciliation:
                  </strong>{" "}
                  {reconciliationMessage}
                </p>

                <p>
                  <strong>
                    Verification status:
                  </strong>{" "}
                  {reconciliationStatus}
                </p>

              </div>

              <div className="evidence-box">

                <span>
                  FINANCIAL COMPARISON
                </span>

                <div className="amount-comparison">

                  <div className="amount-card">

                    <span>
                      EXPECTED
                    </span>

                    <strong>
                      {formatMoney(
                        expectedAmount,
                        currency,
                      )}
                    </strong>

                  </div>

                  <div className="amount-card">

                    <span>
                      OBSERVED
                    </span>

                    <strong>
                      {formatMoney(
                        observedAmount,
                        currency,
                      )}
                    </strong>

                  </div>

                  <div className="amount-card">

                    <span>
                      DIFFERENCE
                    </span>

                    <strong>
                      {formatMoney(
                        difference,
                        currency,
                      )}
                    </strong>

                  </div>

                </div>

              </div>

              <div className="evidence-box">

                <span>
                  RECONCILIATION EVIDENCE
                </span>

                {selectedEvidence ? (
                  <pre>
                    {JSON.stringify(
                      selectedEvidence,
                      null,
                      2,
                    )}
                  </pre>
                ) : (
                  <p>
                    No structured evidence
                    available.
                  </p>
                )}

              </div>

              <div className="evidence-box">

                <span>
                  AGENT RECOMMENDATION
                </span>

                <p>
                  {selectedCase.recommendation ||
                    selectedInvestigation?.recommendation ||
                    "Human investigation required."}
                </p>

                <p>
                  FeeFlow is a control and
                  investigation layer. It does
                  not execute, release or modify
                  the underlying financial
                  transaction.
                </p>

              </div>

              <div className="evidence-box">

                <span>
                  CASE AUDIT HISTORY
                </span>

                {caseHistory.length >
                0 ? (
                  <div className="review-list">

                    {caseHistory
                      .slice(0, 8)
                      .map(
                        (
                          record,
                          index,
                        ) => (
                          <div
                            className="review-item"
                            key={`${selectedId}-history-${index}`}
                          >

                            <div>

                              <strong>
                                {pretty(
                                  record?.event,
                                )}
                              </strong>

                              <p>
                                {record?.reason ||
                                  record?.message ||
                                  "Audit event recorded."}
                              </p>

                              <small>
                                {formatDate(
                                  record?.timestamp,
                                )}
                              </small>

                            </div>

                            <span>
                              {pretty(
                                record?.decision ||
                                  record?.agent_action ||
                                  record?.control_action ||
                                  "RECORDED",
                              )}
                            </span>

                          </div>
                        ),
                      )}

                  </div>
                ) : (
                  <p>
                    No additional audit
                    history for this case.
                  </p>
                )}

              </div>

              {selectedCase.requires_human &&
                normalizeStatus(
                  selectedReview?.status ||
                    selectedCase.status,
                ) !==
                  "RESOLVED" && (

                <div className="modal-actions">

                  <div className="evidence-box">

                    <span>
                      HUMAN ACTION REQUIRED
                    </span>

                    <p>
                      Record an explicit
                      workflow decision with
                      reviewer identity and an
                      auditable reason.
                    </p>

                    <select
                      value={decision}
                      onChange={(event) =>
                        setDecision(
                          event.target.value,
                        )
                      }
                    >

                      <option value="">
                        Select decision
                      </option>

                      {DECISIONS.map(
                        (item) => (
                          <option
                            key={item}
                            value={item}
                          >
                            {pretty(item)}
                          </option>
                        ),
                      )}

                    </select>

                    <input
                      value={reviewer}
                      onChange={(event) =>
                        setReviewer(
                          event.target.value,
                        )
                      }
                      placeholder="Reviewer identity"
                    />

                    <textarea
                      value={decisionReason}
                      onChange={(event) =>
                        setDecisionReason(
                          event.target.value,
                        )
                      }
                      placeholder="Why was this decision made and what should happen next?"
                    />

                    <button
                      className="primary-button"
                      disabled={
                        isSubmittingDecision ||
                        !decision ||
                        !decisionReason.trim() ||
                        !reviewer.trim()
                      }
                      onClick={
                        handleDecision
                      }
                    >
                      {isSubmittingDecision
                        ? "Recording..."
                        : "Record Human Decision"}
                    </button>

                  </div>

                </div>
              )}

            </div>

          </div>
        )}

      </main>

    </div>
  );
}

export default App;