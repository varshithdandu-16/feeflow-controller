const API_BASE_URL = "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json();
}

export async function checkHealth() {
  return request("/health");
}

export async function runControls() {
  return request("/controls/run", {
    method: "POST",
  });
}

export async function runAgent() {
  return request("/agent/run", {
    method: "POST",
  });
}

export async function getReviewCases() {
  return request("/review/cases", {
    method: "POST",
  });
}

export async function submitReviewDecision(
  caseId,
  decision,
  reason,
  reviewer,
) {
  return request(
    `/review/cases/${encodeURIComponent(caseId)}/decision`,
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