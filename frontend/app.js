const API_URL = "http://localhost:8000/v1/legal/contract/risk";

const clauseInput = document.getElementById("clause-input");
const checkBtn = document.getElementById("check-btn");
const resultEl = document.getElementById("result");
const errorEl = document.getElementById("error");
const riskBadge = document.getElementById("risk-badge");
const semanticCategory = document.getElementById("semantic-category");
const semanticSimilarity = document.getElementById("semantic-similarity");
const heuristicFlags = document.getElementById("heuristic-flags");
const heuristicSeverity = document.getElementById("heuristic-severity");
const confidenceEl = document.getElementById("confidence");
const disagreementWarning = document.getElementById("disagreement-warning");

checkBtn.addEventListener("click", async () => {
  const clause = clauseInput.value.trim();
  if (!clause) return;

  errorEl.classList.add("hidden");
  resultEl.classList.add("hidden");
  checkBtn.disabled = true;
  checkBtn.textContent = "Checking...";

  try {
    const resp = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clause }),
    });

    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed with status ${resp.status}`);
    }

    const payload = await resp.json();
    render(payload);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = "Check risk";
  }
});

function render(payload) {
  const { data, meta } = payload;

  riskBadge.textContent = `${data.risk_category} risk (${(data.risk_score * 100).toFixed(0)}%)`;
  riskBadge.className = `risk-badge ${data.risk_category}`;

  semanticCategory.textContent = data.semantic.matched_category || "no match";
  semanticSimilarity.textContent = `${(data.semantic.similarity * 100).toFixed(1)}%`;

  heuristicFlags.textContent = data.heuristic.flags.length
    ? data.heuristic.flags.join(", ")
    : "none";
  heuristicSeverity.textContent = data.heuristic.severity;

  confidenceEl.textContent = `${(meta.trust.confidence * 100).toFixed(0)}%`;

  disagreementWarning.classList.toggle("hidden", data.signals_agree);

  resultEl.classList.remove("hidden");
}
