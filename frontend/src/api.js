const API_BASE_URL =
  "http://127.0.0.1:8000";

async function request(
  endpoint,
  options = {},
) {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        "Content-Type":
          "application/json",
        ...(options.headers || {}),
      },
    },
  );

  if (!response.ok) {
    let message =
      `Request failed with status ${response.status}`;

    try {
      const data =
        await response.json();

      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return response.json();
}

export function checkHealth() {
  return request("/health");
}

export function runControls() {
  return request(
    "/controls/run",
    {
      method: "POST",
    },
  );
}

export function runAgent() {
  return request(
    "/agent/run",
    {
      method: "POST",
    },
  );
}

export function getLatestAgentRun() {
  return request(
    "/agent/latest",
  );
}

export function getReviewCases() {
  return request(
    "/review/cases",
    {
      method: "POST",
    },
  );
}

export function submitReviewDecision(
  caseId,
  decision,
  reason,
  reviewer,
) {
  return request(
    `/review/cases/${encodeURIComponent(
      caseId,
    )}/decision`,
    {
      method: "POST",
      body: JSON.stringify({
        decision,
        reason,
        reviewer,
      }),
    },
  );
}

export function verifyTransaction(
  caseId,
) {
  if (!caseId?.trim()) {
    throw new Error(
      "A transaction case ID is required.",
    );
  }

  return request(
    "/verify/transaction",
    {
      method: "POST",
      body: JSON.stringify({
        case_id: caseId.trim(),
      }),
    },
  );
}

export function getAuditRecords() {
  return request(
    "/audit/records",
  );
}