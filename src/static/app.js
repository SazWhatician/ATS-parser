/**
 * ATS Resume Parser & Evaluation Engine — Client Application
 * Author: SazWhatician
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("file-info");
  const fileNameDisplay = document.getElementById("file-name");
  const removeFileBtn = document.getElementById("remove-file-btn");
  const jdInput = document.getElementById("jd-input");
  const forceHeuristicCheckbox = document.getElementById("force-heuristic-checkbox");
  const submitBtn = document.getElementById("submit-btn");
  const presetBtns = document.querySelectorAll(".preset-btn");

  const emptyState = document.getElementById("empty-state");
  const loadingState = document.getElementById("loading-state");
  const resultsState = document.getElementById("results-state");

  // Output elements
  const avatarInitials = document.getElementById("avatar-initials");
  const candidateName = document.getElementById("candidate-name");
  const candidateDomain = document.getElementById("candidate-domain");
  const candidateContacts = document.getElementById("candidate-contacts");
  const candidateSummary = document.getElementById("candidate-summary");

  const overallScoreNum = document.getElementById("overall-score-num");
  const scoreMatchLevel = document.getElementById("score-match-level");
  const scoreTech = document.getElementById("score-tech");
  const scoreExp = document.getElementById("score-exp");
  const scoreEdu = document.getElementById("score-edu");
  const scoreQual = document.getElementById("score-qual");
  const recommendationText = document.getElementById("recommendation-text");

  const strengthsList = document.getElementById("strengths-list");
  const gapsList = document.getElementById("gaps-list");

  const experienceList = document.getElementById("experience-list");
  const categorizedSkillsContainer = document.getElementById("categorized-skills-container");
  const educationList = document.getElementById("education-list");
  const jsonCode = document.getElementById("json-code");
  const copyJsonBtn = document.getElementById("copy-json-btn");

  const telemetryTime = document.getElementById("telemetry-time");
  const telemetryMode = document.getElementById("telemetry-mode");
  const engineStatusText = document.getElementById("engine-status-text");

  let selectedFile = null;
  let latestPayload = null;

  // Presets definition
  const PRESETS = {
    backend: `Job Title: Senior Backend Engineer
Requirements:
- 4+ years of professional backend engineering experience with Python or Go.
- High proficiency with FastAPI, Django, and relational databases (PostgreSQL).
- Experience with Docker, Redis, and building high-throughput microservices.
- Degree in Computer Science, Software Engineering, or equivalent experience.
Nice to Have:
- Kubernetes, Kafka, and cloud deployment on AWS or GCP.`,

    frontend: `Job Title: Senior Frontend Engineer
Requirements:
- 3+ years of professional web application engineering.
- Deep expertise in TypeScript, JavaScript (ES6+), React, and Next.js.
- Strong understanding of state management, Tailwind CSS, and REST/GraphQL APIs.
- Experience with unit testing, responsive design, and frontend performance optimization.`,

    ml: `Job Title: Machine Learning & AI Engineer
Requirements:
- 3+ years of practical experience deploying machine learning models into production.
- Expert Python skills with PyTorch, TensorFlow, Scikit-learn, and Pandas.
- Experience with LLM prompt engineering, vector embeddings, and RAG architectures.
- Bachelor's or Master's degree in CS, Math, Data Science, or related quantitative field.`
  };

  // 1. Initial System Health Ping
  fetch("/api/v1/health")
    .then(res => res.json())
    .then(data => {
      if (data.has_llm_key) {
        engineStatusText.textContent = `Engine: LLM Ready (${data.engine_mode.toUpperCase()})`;
      } else {
        engineStatusText.textContent = "Engine: 100% Offline Heuristic";
      }
    })
    .catch(() => {
      engineStatusText.textContent = "Engine: Offline Mode";
    });

  // 2. Drag & Drop File Handling
  ["dragenter", "dragover"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("drag-active");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("drag-active");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validExtensions = [".pdf", ".docx", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      alert(`Unsupported file format '${ext}'. Please upload a .pdf, .docx, or .txt file.`);
      return;
    }

    selectedFile = file;
    fileNameDisplay.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    fileInfo.classList.remove("hidden");
    submitBtn.removeAttribute("disabled");
  }

  removeFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = "";
    fileInfo.classList.add("hidden");
    submitBtn.setAttribute("disabled", "true");
  });

  // 3. Preset Buttons
  presetBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const presetKey = btn.getAttribute("data-preset");
      if (PRESETS[presetKey]) {
        jdInput.value = PRESETS[presetKey];
      }
    });
  });

  // 4. Tab Navigation
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabTarget = btn.getAttribute("data-tab");
      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(`tab-${tabTarget}`);
      if (targetPane) {
        targetPane.classList.add("active");
      }
    });
  });

  // 5. Form Submission
  document.getElementById("evaluation-form").addEventListener("submit", (e) => {
    e.preventDefault();
    runEvaluation();
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      if (selectedFile) {
        runEvaluation();
      }
    }
  });

  function runEvaluation() {
    if (!selectedFile) return;

    // Switch states
    emptyState.classList.add("hidden");
    resultsState.classList.add("hidden");
    loadingState.classList.remove("hidden");

    const formData = new FormData();
    formData.append("file", selectedFile);
    if (jdInput.value.trim()) {
      formData.append("job_description", jdInput.value.trim());
    }
    formData.append("force_heuristic", forceHeuristicCheckbox.checked);

    fetch("/api/v1/analyze", {
      method: "POST",
      body: formData
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(err => { throw new Error(err.detail || "Error evaluating resume"); });
        }
        return res.json();
      })
      .then(data => {
        latestPayload = data;
        renderResults(data);
      })
      .catch(err => {
        alert("Evaluation Error: " + err.message);
        emptyState.classList.remove("hidden");
      })
      .finally(() => {
        loadingState.classList.add("hidden");
      });
  }

  // 6. Render Results Function
  function renderResults(data) {
    const profile = data.profile;
    const report = data.score_report;

    // A. Candidate Card
    const name = profile.contact.name || "Candidate Profile";
    candidateName.textContent = name;
    avatarInitials.textContent = name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase() || "CV";
    candidateDomain.textContent = profile.primary_domain || "Engineering";

    // Contacts
    candidateContacts.innerHTML = "";
    if (profile.contact.email) {
      candidateContacts.innerHTML += `<span class="contact-pill">📧 ${escapeHtml(profile.contact.email)}</span>`;
    }
    if (profile.contact.phone) {
      candidateContacts.innerHTML += `<span class="contact-pill">📞 ${escapeHtml(profile.contact.phone)}</span>`;
    }
    if (profile.contact.location) {
      candidateContacts.innerHTML += `<span class="contact-pill">📍 ${escapeHtml(profile.contact.location)}</span>`;
    }
    if (profile.contact.linkedin) {
      candidateContacts.innerHTML += `<a href="${formatUrl(profile.contact.linkedin)}" target="_blank" class="contact-pill highlight-link">🔗 LinkedIn</a>`;
    }
    if (profile.contact.github) {
      candidateContacts.innerHTML += `<a href="${formatUrl(profile.contact.github)}" target="_blank" class="contact-pill highlight-link">💻 GitHub</a>`;
    }

    // Summary
    candidateSummary.textContent = profile.summary || "No professional summary statement detected in resume.";

    // B. Scoreboard
    if (report) {
      const score = Math.round(report.overall_score);
      overallScoreNum.textContent = `${score}%`;
      scoreMatchLevel.textContent = report.match_level;

      overallScoreNum.className = "score-numeric " + (score >= 75 ? "high" : score >= 50 ? "mid" : "low");

      const cats = report.categories || {};
      scoreTech.textContent = cats.technical_skills ? `${cats.technical_skills.score}%` : "--";
      scoreExp.textContent = cats.experience ? `${cats.experience.score}%` : "--";
      scoreEdu.textContent = cats.education ? `${cats.education.score}%` : "--";
      scoreQual.textContent = cats.quality ? `${cats.quality.score}%` : "--";

      recommendationText.textContent = report.recommendation;

      // Strengths & Gaps
      strengthsList.innerHTML = (report.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
      gapsList.innerHTML = (report.gaps || []).map(g => `<li>${escapeHtml(g)}</li>`).join("");
    }

    // C. Timeline / Experience Tab
    if (profile.experience && profile.experience.length > 0) {
      experienceList.innerHTML = profile.experience.map(exp => `
        <div class="exp-item">
          <div class="exp-role">${escapeHtml(exp.role)}</div>
          <div class="exp-company">${escapeHtml(exp.company)}${exp.location ? " • " + escapeHtml(exp.location) : ""}</div>
          <div class="exp-dates">${escapeHtml(exp.start_date || "")} - ${escapeHtml(exp.end_date || "Present")} (${escapeHtml(exp.duration || "")})</div>
          ${exp.highlights && exp.highlights.length ? `
            <ul class="exp-highlights">
              ${exp.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join("")}
            </ul>
          ` : ""}
        </div>
      `).join("");
    } else {
      experienceList.innerHTML = "<p class='empty-text'>No discrete work experience entries detected.</p>";
    }

    // D. Categorized Skills Tab
    if (profile.categorized_skills && Object.keys(profile.categorized_skills).length > 0) {
      categorizedSkillsContainer.innerHTML = Object.entries(profile.categorized_skills).map(([cat, skills]) => `
        <div>
          <div class="skill-category-title">${escapeHtml(cat)} (${skills.length})</div>
          <div class="chips-row">
            ${skills.map(s => `<span class="skill-chip">${escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
      `).join("");
    } else if (profile.skills && profile.skills.length > 0) {
      categorizedSkillsContainer.innerHTML = `
        <div class="chips-row">
          ${profile.skills.map(s => `<span class="skill-chip">${escapeHtml(s)}</span>`).join("")}
        </div>
      `;
    } else {
      categorizedSkillsContainer.innerHTML = "<p class='empty-text'>No technical skills extracted.</p>";
    }

    // E. Education Tab
    if (profile.education && profile.education.length > 0) {
      educationList.innerHTML = profile.education.map(edu => `
        <div class="edu-card">
          <div class="edu-inst">${escapeHtml(edu.institution)}</div>
          <div class="edu-degree">${escapeHtml(edu.degree || "Degree")}</div>
          ${edu.graduation_year ? `<div class="edu-year">Graduated: ${escapeHtml(edu.graduation_year)}</div>` : ""}
        </div>
      `).join("");
    } else {
      educationList.innerHTML = "<p class='empty-text'>No academic degree entries detected.</p>";
    }

    // F. Raw JSON Tab
    jsonCode.textContent = JSON.stringify(data, null, 2);

    // G. Telemetry
    telemetryTime.textContent = `Execution Time: ${data.processing_time_ms} ms`;
    telemetryMode.textContent = `Engine Mode: ${data.engine_mode.toUpperCase()}`;

    resultsState.classList.remove("hidden");
  }

  // 7. Copy JSON Helper
  copyJsonBtn.addEventListener("click", () => {
    if (!latestPayload) return;
    navigator.clipboard.writeText(JSON.stringify(latestPayload, null, 2))
      .then(() => {
        copyJsonBtn.textContent = "Copied!";
        setTimeout(() => { copyJsonBtn.textContent = "Copy JSON"; }, 2000);
      });
  });

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatUrl(url) {
    if (!url) return "#";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    return "https://" + url;
  }
});
