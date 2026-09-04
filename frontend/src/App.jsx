import { useEffect, useMemo, useState } from "react";
import "./App.css";
import {
  checkHealth,
  runAgent,
  getReviewCases,
  submitReviewDecision,
} from "./api";

function App() {
  const [activeView, setActiveView] = useState("overview");
  const [agentData, setAgentData] = useState(null);
  const [reviewCases, setReviewCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);

  const [backendStatus, setBackendStatus] = useState("Checking backend...");
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingReviews, setIsLoadingReviews] = useState(false);
  const [error, setError] = useState("");

  const [decision, setDecision] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [reviewer, setReviewer] = useState("Horizon Risk Team");

  // --------------------------------------------------
  // BACKEND HEALTH
  // --------------------------------------------------

  useEffect(() => {
    async function loadHealth() {
      try {
        await checkHealth();
        setBackendStatus("Backend ready");
      } catch {
        setBackendStatus("Backend unavailable");
      }
    }

    loadHealth();
  }, []);

  // --------------------------------------------------
  // RUN AGENT
  // --------------------------------------------------

  async function handleRunAgent() {
    setIsRunning(true);
    setError("");

    try {
      const result = await runAgent();

      setAgentData(result);

      // Load the actual review queue after the agent finishes.
      try {
        const reviews = await getReviewCases();
        setReviewCases(
          Array.isArray(reviews)
            ? reviews
            : reviews?.cases || reviews?.review_cases || [],
        );
      } catch {
        // Agent result is still useful even if review loading fails.
        setReviewCases(result.review_cases || []);
      }

      setBackendStatus("Backend ready");
      setActiveView("overview");
    } catch (err) {
      setError(err.message || "Unable to run the agent.");
    } finally {
      setIsRunning(false);
    }
  }

  // --------------------------------------------------
  // LOAD REVIEW QUEUE
  // --------------------------------------------------

  async function handleLoadReviews() {
    setIsLoadingReviews(true);
    setError("");

    try {
      const result = await getReviewCases();

      const cases = Array.isArray(result)
        ? result
        : result?.cases || result?.review_cases || [];

      setReviewCases(cases);
    } catch (err) {
      setError(err.message || "Unable to load review cases.");
    } finally {
      setIsLoadingReviews(false);
    }
  }

  // --------------------------------------------------
  // HUMAN DECISION
  // --------------------------------------------------

  async function handleDecision() {
    if (!selectedCase || !decision) {
      return;
    }

    setError("");

    try {
      await submitReviewDecision(
        selectedCase.case_id,
        decision,
        decisionReason,
        reviewer,
      );

      setDecision("");
      setDecisionReason("");

      await handleLoadReviews();

      setSelectedCase(null);
    } catch (err) {
      setError(err.message || "Unable to submit review decision.");
    }
  }

  // --------------------------------------------------
  // AGENT SUMMARY
  // --------------------------------------------------

  const summary = agentData?.summary || {
    clear: 0,
    monitor: 0,
    human_review: 0,
    blocked: 0,
  };

  const casesProcessed = agentData?.cases_processed || 0;

  const clearPercentage = useMemo(() => {
    if (!casesProcessed) return "0.0";
    return ((summary.clear / casesProcessed) * 100).toFixed(1);
  }, [summary.clear, casesProcessed]);

  const reviewPercentage = useMemo(() => {
    if (!casesProcessed) return "0.0";
    return ((summary.human_review / casesProcessed) * 100).toFixed(1);
  }, [summary.human_review, casesProcessed]);

  const blockedPercentage = useMemo(() => {
    if (!casesProcessed) return "0.0";
    return ((summary.blocked / casesProcessed) * 100).toFixed(1);
  }, [summary.blocked, casesProcessed]);

  const assessments = agentData?.assessments || [];
  const investigations = agentData?.investigations || [];
  const auditRecords = agentData?.audit_records || [];

  // --------------------------------------------------
  // HELPERS
  // --------------------------------------------------

  function getAssessment(caseId) {
    return assessments.find(
      (item) => item.case_id === caseId,
    );
  }

  function getInvestigation(caseId) {
    return investigations.find(
      (item) => item.case_id === caseId,
    );
  }

  function getStatus(caseId) {
    const assessment = getAssessment(caseId);

    if (!assessment) {
      return "UNKNOWN";
    }

    if (assessment.action === "AUTO_CLEAR") {
      return "CLEAR";
    }

    if (assessment.action === "CLEAR") {
      return "CLEAR";
    }

    if (assessment.action === "HUMAN_REVIEW") {
      return "HUMAN_REVIEW";
    }

    if (
      assessment.action === "BLOCK" ||
      assessment.action === "BLOCKED"
    ) {
      return "BLOCKED";
    }

    return assessment.action;
  }

  function getReason(caseId) {
    const assessment = getAssessment(caseId);
    const investigation = getInvestigation(caseId);

    return (
      investigation?.explanation ||
      investigation?.finding ||
      assessment?.reason ||
      "No explanation available."
    );
  }

  function openCase(caseItem) {
    setSelectedCase(caseItem);
    setDecision("");
    setDecisionReason("");
  }

  // --------------------------------------------------
  // CASES
  // --------------------------------------------------

  const displayedCases = assessments.map((assessment) => {
    const investigation = getInvestigation(
      assessment.case_id,
    );

    return {
      case_id: assessment.case_id,
      action: assessment.action,
      status: getStatus(assessment.case_id),
      reason: getReason(assessment.case_id),
      requires_human: assessment.requires_human,
      finding: investigation?.finding,
      risk: investigation?.risk,
      evidence: investigation?.evidence,
      recommendation: investigation?.recommendation,
      confidence: investigation?.confidence,
    };
  });

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-mark">F</div>

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
              activeView === "overview" ? "active" : ""
            }`}
            onClick={() => setActiveView("overview")}
          >
            <span>◈</span>
            Overview
          </button>

          <button
            className={`nav-item ${
              activeView === "controls" ? "active" : ""
            }`}
            onClick={() => setActiveView("controls")}
          >
            <span>✓</span>
            Controls
          </button>

          <button
            className={`nav-item ${
              activeView === "reviews" ? "active" : ""
            }`}
            onClick={() => {
              setActiveView("reviews");
              handleLoadReviews();
            }}
          >
            <span>!</span>
            Human Review

            {summary.human_review > 0 && (
              <span className="nav-count">
                {summary.human_review}
              </span>
            )}
          </button>

          <button
            className={`nav-item ${
              activeView === "audit" ? "active" : ""
            }`}
            onClick={() => setActiveView("audit")}
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
                {backendStatus === "Backend ready"
                  ? "System operational"
                  : backendStatus}
              </strong>

              <small>
                {backendStatus === "Backend ready"
                  ? "Control engine online"
                  : "Checking control engine"}
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
              Autonomous financial investigation with deterministic
              controls and human oversight.
            </p>
          </div>

          <div className="topbar-actions">

            <div className="live-indicator">
              <span className="status-dot" />
              {backendStatus}
            </div>

            <button
              className="run-button"
              onClick={handleRunAgent}
              disabled={isRunning}
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

        {/* OVERVIEW */}

        {activeView === "overview" && (
          <>

            <section className="metrics-grid">

              <div className="metric-card">
                <div className="metric-label">
                  CASES PROCESSED
                </div>

                <div className="metric-value">
                  {agentData ? casesProcessed : "—"}
                </div>

                <div className="metric-meta">
                  <span className="positive">
                    {agentData ? "Live" : "Ready"}
                  </span>
                  Financial cases evaluated
                </div>
              </div>

              <div className="metric-card success">

                <div className="metric-label">
                  AUTO CLEARED
                </div>

                <div className="metric-value">
                  {agentData ? summary.clear : "—"}
                </div>

                <div className="metric-meta">
                  <span className="positive">
                    {agentData
                      ? `${clearPercentage}%`
                      : "—"}
                  </span>
                  Passed controls automatically
                </div>

              </div>

              <div className="metric-card warning">

                <div className="metric-label">
                  HUMAN REVIEW
                </div>

                <div className="metric-value">
                  {agentData
                    ? summary.human_review
                    : "—"}
                </div>

                <div className="metric-meta">
                  <span className="warning-text">
                    {agentData
                      ? "Attention"
                      : "Waiting"}
                  </span>
                  Requires reviewer investigation
                </div>

              </div>

              <div className="metric-card critical">

                <div className="metric-label">
                  BLOCKED
                </div>

                <div className="metric-value">
                  {agentData
                    ? summary.blocked
                    : "—"}
                </div>

                <div className="metric-meta">
                  <span className="positive">
                    {agentData
                      ? `${blockedPercentage}%`
                      : "—"}
                  </span>
                  Cases stopped by policy
                </div>

              </div>

            </section>

            <section className="dashboard-grid">

              {/* CONTROL RESULTS */}

              <div className="panel control-panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Agent Assessments
                    </h2>

                    <p>
                      Latest financial control decisions
                    </p>
                  </div>

                  <button
                    className="text-button"
                    onClick={() =>
                      setActiveView("controls")
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
                        <th>ACTION</th>
                        <th>REQUIREMENT</th>
                        <th>REASON</th>
                      </tr>
                    </thead>

                    <tbody>

                      {displayedCases
                        .slice(0, 8)
                        .map((item) => (

                          <tr
                            key={item.case_id}
                            onClick={() =>
                              openCase(item)
                            }
                          >

                            <td>
                              <strong>
                                {item.case_id}
                              </strong>
                            </td>

                            <td>
                              <span
                                className={`status-badge ${item.status
                                  .toLowerCase()
                                  .replace("_", "-")}`}
                              >
                                {item.status.replace(
                                  "_",
                                  " ",
                                )}
                              </span>
                            </td>

                            <td>
                              {item.requires_human
                                ? "Human"
                                : "Automatic"}
                            </td>

                            <td>
                              {item.reason}
                            </td>

                          </tr>

                        ))}

                      {!agentData && (
                        <tr>
                          <td colSpan="4">
                            Run the agent to evaluate
                            financial cases.
                          </td>
                        </tr>
                      )}

                    </tbody>

                  </table>

                </div>

              </div>

              {/* PIPELINE */}

              <div className="panel activity-panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Agent Pipeline
                    </h2>

                    <p>
                      Current workflow distribution
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
                          Deterministic controls passed
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
                          agentData
                            ? clearPercentage
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
                          Agent escalations
                        </small>
                      </div>

                    </div>

                    <strong>
                      {agentData
                        ? summary.human_review
                        : "—"}
                    </strong>

                  </div>

                  <div className="progress-track">

                    <div
                      className="progress-fill review-fill"
                      style={{
                        width: `${
                          agentData
                            ? reviewPercentage
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
                          Stopped by control policy
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
                      {agentData
                        ? "Agent investigation completed"
                        : "Agent ready"}
                    </strong>

                    <p>
                      {agentData
                        ? `Evaluated ${casesProcessed} financial cases and routed exceptions for appropriate action.`
                        : "Run the agent to begin the financial control workflow."}
                    </p>

                  </div>

                </div>

              </div>

            </section>

            <section className="panel review-panel">

              <div className="panel-header">

                <div>

                  <h2>
                    Human Review Queue
                  </h2>

                  <p>
                    Exceptions requiring human investigation
                  </p>

                </div>

                <button
                  className="review-button"
                  onClick={() => {
                    setActiveView("reviews");
                    handleLoadReviews();
                  }}
                >
                  Open Review Queue →
                </button>

              </div>

              <div className="review-summary">

                <div className="review-summary-number">
                  {agentData
                    ? summary.human_review
                    : "—"}
                </div>

                <div>

                  <strong>
                    Cases require human attention
                  </strong>

                  <p>
                    The agent has identified exceptions
                    that cannot be resolved automatically.
                  </p>

                </div>

                <div className="review-rule">

                  <span className="status-dot warning-dot" />

                  Human decision required

                </div>

              </div>

            </section>

          </>
        )}

        {/* CONTROLS */}

        {activeView === "controls" && (

          <section className="panel page-panel">

            <div className="panel-header">

              <div>
                <h2>
                  Agent Control Assessments
                </h2>

                <p>
                  Decisions produced by the FeeFlow agent
                </p>
              </div>

              <button
                className="run-button"
                onClick={handleRunAgent}
                disabled={isRunning}
              >
                {isRunning
                  ? "Running..."
                  : "Run Agent"}
              </button>

            </div>

            <div className="table-wrapper">

              <table>

                <thead>
                  <tr>
                    <th>CASE</th>
                    <th>ACTION</th>
                    <th>HUMAN REQUIRED</th>
                    <th>REASON</th>
                  </tr>
                </thead>

                <tbody>

                  {displayedCases.map((item) => (

                    <tr
                      key={item.case_id}
                      onClick={() =>
                        openCase(item)
                      }
                    >

                      <td>
                        <strong>
                          {item.case_id}
                        </strong>
                      </td>

                      <td>
                        {item.status}
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

                  ))}

                </tbody>

              </table>

            </div>

          </section>

        )}

        {/* HUMAN REVIEW */}

        {activeView === "reviews" && (

          <section className="panel page-panel">

            <div className="panel-header">

              <div>
                <h2>
                  Human Review Queue
                </h2>

                <p>
                  Agent escalations awaiting human decision
                </p>
              </div>

              <button
                className="review-button"
                onClick={handleLoadReviews}
                disabled={isLoadingReviews}
              >
                {isLoadingReviews
                  ? "Loading..."
                  : "Refresh Queue"}
              </button>

            </div>

            <div className="review-list">

              {reviewCases.length === 0 && (

                <div className="empty-state">
                  No review cases currently available.
                </div>

              )}

              {reviewCases.map((reviewCase) => (

                <button
                  key={reviewCase.case_id}
                  className="review-item"
                  onClick={() =>
                    openCase(reviewCase)
                  }
                >

                  <div>

                    <strong>
                      {reviewCase.case_id}
                    </strong>

                    <p>
                      {reviewCase.finding ||
                        reviewCase.explanation ||
                        "Investigation available"}
                    </p>

                  </div>

                  <span>
                    {reviewCase.status ||
                      "PENDING"}
                  </span>

                </button>

              ))}

            </div>

          </section>

        )}

        {/* AUDIT */}

        {activeView === "audit" && (

          <section className="panel page-panel">

            <div className="panel-header">

              <div>
                <h2>
                  Audit Trail
                </h2>

                <p>
                  Evidence of agent decisions and control execution
                </p>
              </div>
            </div>

            <div className="table-wrapper">

              <table>

                <thead>
                  <tr>
                    <th>CASE</th>
                    <th>ACTION</th>
                    <th>SEVERITY</th>
                    <th>EXCEPTION</th>
                  </tr>
                </thead>

                <tbody>

                  {auditRecords.map(
                    (record, index) => (

                      <tr key={index}>

                        <td>
                          {record.case_id ||
                            record.assessment_id ||
                            "—"}
                        </td>

                        <td>
                          {record.control_action ||
                            record.action ||
                            "—"}
                        </td>

                        <td>
                          {record.severity ||
                            "—"}
                        </td>

                        <td>
                          {record.exception_code ||
                            "None"}
                        </td>

                      </tr>

                    ),
                  )}

                  {auditRecords.length === 0 && (

                    <tr>
                      <td colSpan="4">
                        Run the agent to generate
                        audit records.
                      </td>
                    </tr>

                  )}

                </tbody>

              </table>

            </div>

          </section>

        )}

        {/* CASE MODAL */}

        {selectedCase && (

          <div
            className="case-overlay"
            onClick={() =>
              setSelectedCase(null)
            }
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
                    AGENT CASE
                  </div>

                  <h2>
                    {selectedCase.case_id}
                  </h2>

                </div>

                <button
                  className="close-button"
                  onClick={() =>
                    setSelectedCase(null)
                  }
                >
                  ×
                </button>

              </div>

              <div className="case-details">

                <div>
                  <span>Status</span>

                  <strong>
                    {selectedCase.status ||
                      selectedCase.action ||
                      "—"}
                  </strong>
                </div>

                <div>
                  <span>Risk</span>

                  <strong>
                    {selectedCase.risk ||
                      "Not available"}
                  </strong>
                </div>

                <div>
                  <span>Confidence</span>

                  <strong>
                    {selectedCase.confidence != null
                      ? `${(
                          selectedCase.confidence *
                          100
                        ).toFixed(0)}%`
                      : "Not available"}
                  </strong>
                </div>

                <div>
                  <span>Human Required</span>

                  <strong>
                    {selectedCase.requires_human
                      ? "YES"
                      : "NO"}
                  </strong>
                </div>

              </div>

              <div className="evidence-box">

                <span>
                  AGENT FINDING
                </span>

                <p>
                  {selectedCase.finding ||
                    selectedCase.reason ||
                    selectedCase.explanation ||
                    "No finding available."}
                </p>

              </div>

              {selectedCase.evidence && (

                <div className="evidence-box">

                  <span>
                    EVIDENCE
                  </span>

                  <pre>
                    {JSON.stringify(
                      selectedCase.evidence,
                      null,
                      2,
                    )}
                  </pre>

                </div>

              )}

              {selectedCase.requires_human && (

                <div className="modal-actions">

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

                    <option value="APPROVE">
                      Approve
                    </option>

                    <option value="REJECT">
                      Reject
                    </option>

                    <option value="ESCALATE">
                      Escalate
                    </option>

                  </select>

                  <input
                    value={reviewer}
                    onChange={(event) =>
                      setReviewer(
                        event.target.value,
                      )
                    }
                    placeholder="Reviewer"
                  />

                  <textarea
                    value={decisionReason}
                    onChange={(event) =>
                      setDecisionReason(
                        event.target.value,
                      )
                    }
                    placeholder="Decision reason"
                  />

                  <button
                    className="primary-button"
                    disabled={!decision}
                    onClick={handleDecision}
                  >
                    Submit Decision
                  </button>

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