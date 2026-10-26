// In-page AI code analyzer widget (AJAX, no page reload).

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("analyzer-form");
  if (!form) return;

  const codeField = document.getElementById("code-input");
  const langField = document.getElementById("language-select");
  const submitBtn = document.getElementById("analyze-btn");
  const resultBox = document.getElementById("analyzer-result");

  const severityBadge = (severity) =>
    `<span class="badge badge-${severity || "info"}">${(severity || "info").toUpperCase()}</span>`;

  function escapeHtml(str) {
    return (str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderResult(data) {
    const statusBadge = data.has_error
      ? '<span class="badge badge-danger">ISSUE FOUND</span>'
      : '<span class="badge badge-success">LOOKS GOOD</span>';

    const sourceBadge = data.ai_powered
      ? '<span class="badge badge-info">🤖 AI Review</span>'
      : '<span class="badge badge-info">⚙️ Static Analysis</span>';

    let issuesHtml = "";
    if (data.issues && data.issues.length) {
      issuesHtml = `<ul class="issue-list">${data.issues
        .map(
          (i) => `<li class="issue-item">
            <span class="line-tag">${i.line ? "L" + i.line : "—"}</span>
            <span>${severityBadge(i.severity)} ${escapeHtml(i.message)}</span>
          </li>`
        )
        .join("")}</ul>`;
    }

    // The corrected-code section: when we actually changed something,
    // show a line-level diff (what was wrong vs. what it should be)
    // instead of just dumping the final code — the correction should
    // be obvious, not something the user has to hunt for.
    let correctionHtml;
    if (data.was_corrected && data.diff && data.diff.length) {
      const diffLines = data.diff
        .map((row) => {
          const prefix = row.type === "added" ? "+ " : row.type === "removed" ? "- " : "  ";
          return `<div class="diff-line diff-${row.type}">${escapeHtml(prefix + row.text)}</div>`;
        })
        .join("");
      correctionHtml = `
        <div class="form-label mt-2">✅ Suggested Correction</div>
        <p style="font-size:13px;color:var(--color-text-faint);margin-bottom:10px;">
          Lines in <span style="color:var(--color-danger);">red</span> are what's wrong in your code;
          lines in <span style="color:var(--color-success);">green</span> are the corrected replacement.
        </p>
        <div class="code-block diff-block">${diffLines}</div>
      `;
    } else if (data.has_error) {
      correctionHtml = `
        <div class="form-label mt-2">Your Code</div>
        <p style="font-size:13px;color:var(--color-text-faint);margin-bottom:10px;">
          This couldn't be safely auto-corrected — please review the issue above and fix it by hand.
        </p>
        <div class="code-block">${escapeHtml(data.fixed_code)}</div>
      `;
    } else {
      correctionHtml = `
        <div class="form-label mt-2">Reviewed Code</div>
        <div class="code-block">${escapeHtml(data.fixed_code)}</div>
      `;
    }

    resultBox.innerHTML = `
      <div class="result-headline">
        ${statusBadge} ${sourceBadge} ${severityBadge(data.severity)}
        <strong>${escapeHtml(data.summary)}</strong>
      </div>
      <p class="result-explanation">${escapeHtml(data.explanation)}</p>
      ${issuesHtml}
      ${correctionHtml}
      <div class="result-actions">
        <button class="btn btn-ghost" id="copy-fixed-btn" type="button">Copy fixed code</button>
        <a class="btn btn-ghost" href="/api/report/${data.id}">Download report</a>
      </div>
    `;
    resultBox.classList.remove("hidden");

    document.getElementById("copy-fixed-btn").addEventListener("click", () => {
      navigator.clipboard.writeText(data.fixed_code || "");
      const btn = document.getElementById("copy-fixed-btn");
      const original = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = original), 1500);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = codeField.value.trim();
    if (!code) {
      codeField.focus();
      return;
    }

    submitBtn.disabled = true;
    const originalLabel = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner"></span> Analyzing…';
    resultBox.classList.add("hidden");

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language: langField.value }),
      });
      const data = await res.json();

      if (!res.ok) {
        resultBox.innerHTML = `<p class="result-explanation">${escapeHtml(
          data.error || "Something went wrong. Please try again."
        )}</p>`;
        resultBox.classList.remove("hidden");
        return;
      }

      renderResult(data);
      if (window.refreshDashboardStats) window.refreshDashboardStats();
    } catch (err) {
      resultBox.innerHTML = `<p class="result-explanation">Network error — please try again.</p>`;
      resultBox.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalLabel;
    }
  });
});
