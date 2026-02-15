/* Japanese Driver's License Practice Test App */

let allQuestions = [];
let filteredQuestions = [];
let currentQuestion = null;
let currentFilter = "all";
let sessionHistory = [];  // last 10 shown question IDs
let sessionCount = 0;
let referenceData = null;
let dangerQueue = [];  // queued sibling sub-questions for current danger scenario

const STORAGE_KEY = "jdl_progress";

// --- Data Loading ---

async function fetchQuestions() {
  const res = await fetch("data/questions.json");
  allQuestions = await res.json();
  applyFilter(currentFilter);
  updateHomeProgress();
}

async function fetchReference() {
  if (referenceData) return referenceData;
  const res = await fetch("data/reference.json");
  referenceData = await res.json();
  return referenceData;
}

// --- Progress (localStorage) ---

function getProgress() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

function getQuestionStatus(id) {
  const p = getProgress()[id];
  if (!p) return "unseen";
  if (p.streak >= 1) return "mastered";
  if (p.streak === 0 && p.wrong > 0) return "wrong";
  return "in_progress";
}

// --- Filtering ---

function applyFilter(filter) {
  currentFilter = filter;
  if (filter === "all") {
    filteredQuestions = allQuestions;
  } else if (filter === "lp") {
    filteredQuestions = allQuestions.filter(q => q.source.startsWith("lp"));
  } else if (filter === "dl") {
    filteredQuestions = allQuestions.filter(q => q.type === "standard" && q.source.startsWith("dl"));
  } else if (filter === "danger") {
    filteredQuestions = allQuestions.filter(q => q.type === "danger");
  }

  // Update active button
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === filter);
  });

  updateHomeProgress();
}

// --- Question Selection Algorithm ---

function pickQuestion() {
  const buckets = { wrong: [], unseen: [], in_progress: [], mastered: [] };

  for (const q of filteredQuestions) {
    const status = getQuestionStatus(q.id);
    buckets[status].push(q);
  }

  // Filter out recently shown questions (anti-repetition)
  const recentSet = new Set(sessionHistory.slice(-10));
  const filterRecent = arr => arr.filter(q => !recentSet.has(q.id));

  const wrongPool = filterRecent(buckets.wrong);
  const unseenPool = filterRecent(buckets.unseen);
  const inProgressPool = filterRecent(buckets.in_progress);
  const masteredPool = filterRecent(buckets.mastered);

  // Only include mastered questions when everything else is done
  const hasNonMastered = wrongPool.length > 0 || unseenPool.length > 0 || inProgressPool.length > 0;

  let chosen = null;

  if (wrongPool.length > 0) {
    chosen = weightedPick([
      [wrongPool, 60],
      [unseenPool, 30],
      [inProgressPool, 10],
    ]);
  } else if (unseenPool.length > 0) {
    chosen = weightedPick([
      [unseenPool, 70],
      [inProgressPool, 30],
    ]);
  } else if (inProgressPool.length > 0) {
    chosen = randomFrom(inProgressPool);
  } else if (masteredPool.length > 0) {
    chosen = randomFrom(masteredPool);
  }

  // Fallback: if anti-repetition filtered everything out, pick from unfiltered (excluding mastered if possible)
  if (!chosen) {
    const nonMastered = [...buckets.wrong, ...buckets.unseen, ...buckets.in_progress];
    if (nonMastered.length > 0) {
      chosen = randomFrom(nonMastered);
    } else {
      chosen = randomFrom(buckets.mastered);
    }
  }

  return chosen;
}

function weightedPick(bucketWeights) {
  // Filter to non-empty buckets
  const valid = bucketWeights.filter(([arr]) => arr.length > 0);
  if (valid.length === 0) return null;

  const totalWeight = valid.reduce((sum, [, w]) => sum + w, 0);
  let r = Math.random() * totalWeight;
  for (const [arr, w] of valid) {
    r -= w;
    if (r <= 0) return randomFrom(arr);
  }
  return randomFrom(valid[valid.length - 1][0]);
}

function randomFrom(arr) {
  if (arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

// --- Home Progress ---

function updateHomeProgress() {
  const progress = getProgress();
  let mastered = 0;
  for (const q of filteredQuestions) {
    if (getQuestionStatus(q.id) === "mastered") mastered++;
  }
  const total = filteredQuestions.length;
  const pct = total > 0 ? Math.round((mastered / total) * 100) : 0;
  document.getElementById("progress-bar").style.width = pct + "%";
  document.getElementById("progress-text").textContent =
    `${mastered} / ${total} mastered (${pct}%)`;
}

// --- Study Flow ---

function showQuestion(q) {
  currentQuestion = q;
  sessionCount++;

  // Source label with question number
  const sourceLabel = q.source.toUpperCase().replace("LP", "LP Exam ").replace("DL", "DL Exam ");
  const qNum = q.id.match(/q(\d+)/)[1].replace(/^0+/, "");
  const typeLabel = q.type === "danger" ? " - Danger Q" + qNum : " - Q" + qNum;
  document.getElementById("question-source").textContent = sourceLabel + typeLabel;

  // Image
  const imgEl = document.getElementById("question-image");
  if (q.has_image && q.image_file) {
    imgEl.src = q.image_file;
    imgEl.style.display = "block";
  } else {
    imgEl.style.display = "none";
    imgEl.src = "";
  }

  // Scenario (danger questions)
  const scenarioEl = document.getElementById("question-scenario");
  if (q.type === "danger" && q.scenario) {
    scenarioEl.textContent = q.scenario;
    scenarioEl.style.display = "block";
  } else {
    scenarioEl.style.display = "none";
  }

  // Question text
  document.getElementById("question-text").textContent = q.text;

  // Counter + danger sub-question indicator
  let counterText = `#${sessionCount}`;
  if (q.type === "danger") {
    const subNum = q.id.match(/_(\d+)$/)[1];
    const totalSibs = allQuestions.filter(o => o.id.startsWith(q.id.replace(/_\d+$/, "_"))).length;
    counterText += `  (${subNum}/${totalSibs})`;
  }
  document.getElementById("study-counter").textContent = counterText;

  // Reset UI
  document.getElementById("answer-buttons").style.display = "flex";
  document.getElementById("result-panel").style.display = "none";

  // Track history
  sessionHistory.push(q.id);
  if (sessionHistory.length > 20) sessionHistory.shift();
}

function submitAnswer(answer) {
  if (!currentQuestion) return;

  const correct = answer === currentQuestion.correct_answer;

  // Update progress
  const progress = getProgress();
  const p = progress[currentQuestion.id] || { correct: 0, wrong: 0, streak: 0 };
  if (correct) {
    p.correct++;
    p.streak++;
  } else {
    p.wrong++;
    p.streak = 0;
    // If a danger sub-question is wrong, mark all siblings as wrong too
    if (currentQuestion.type === "danger") {
      const prefix = currentQuestion.id.replace(/_\d+$/, "_");
      for (const q of allQuestions) {
        if (q.id.startsWith(prefix) && q.id !== currentQuestion.id) {
          const sp = progress[q.id] || { correct: 0, wrong: 0, streak: 0 };
          sp.wrong++;
          sp.streak = 0;
          progress[q.id] = sp;
        }
      }
    }
  }
  progress[currentQuestion.id] = p;
  saveProgress(progress);

  // Show result
  document.getElementById("answer-buttons").style.display = "none";
  const resultPanel = document.getElementById("result-panel");
  resultPanel.style.display = "block";

  const banner = document.getElementById("result-banner");
  const justMastered = correct && p.streak === 1;
  banner.className = "result-banner " + (correct ? "correct" : "incorrect");
  let bannerText = correct ? "Correct!" : "Incorrect - Answer: " + (currentQuestion.correct_answer === "T" ? "TRUE" : "FALSE");
  if (justMastered) bannerText += " Mastered!";
  banner.textContent = bannerText;

  document.getElementById("result-explanation").textContent = currentQuestion.explanation;
}

function getDangerSiblings(q) {
  // Given a danger sub-question like "dl1_q91_1", find all siblings "dl1_q91_*"
  const prefix = q.id.replace(/_\d+$/, "_");
  return allQuestions.filter(other => other.id.startsWith(prefix) && other.id !== q.id)
    .sort((a, b) => a.id.localeCompare(b.id));
}

function nextQuestion() {
  let q;
  if (dangerQueue.length > 0) {
    q = dangerQueue.shift();
  } else {
    q = pickQuestion();
    // If a danger question was picked, queue its siblings
    if (q && q.type === "danger") {
      dangerQueue = getDangerSiblings(q);
    }
  }
  if (q) {
    showQuestion(q);
  }
  updateHomeProgress();
}

// --- Views ---

function showView(viewId) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(viewId).classList.add("active");

  if (viewId === "home") {
    updateHomeProgress();
  } else if (viewId === "study") {
    if (!currentQuestion) nextQuestion();
  } else if (viewId === "reference") {
    renderReference();
  } else if (viewId === "stats") {
    renderStats();
  }
}

// --- Reference View ---

async function renderReference() {
  const container = document.getElementById("reference-content");
  if (container.children.length > 0) return; // already rendered

  const ref = await fetchReference();
  const sections = ref.key_points_to_remember.sections;

  for (const section of sections) {
    const div = document.createElement("div");
    div.className = "accordion-section";

    const header = document.createElement("div");
    header.className = "accordion-header";
    header.textContent = section.title;
    header.addEventListener("click", () => div.classList.toggle("open"));

    const body = document.createElement("div");
    body.className = "accordion-body";

    // Section-level image
    if (section.image_file) {
      const img = document.createElement("img");
      img.src = section.image_file;
      img.alt = section.title;
      img.className = "section-image";
      body.appendChild(img);
    }

    if (section.points) {
      const ul = document.createElement("ul");
      for (const point of section.points) {
        const li = document.createElement("li");
        if (typeof point === "string") {
          li.textContent = point;
        } else {
          li.textContent = point.text;
          if (point.image_file) {
            const img = document.createElement("img");
            img.src = point.image_file;
            img.alt = point.text;
            li.appendChild(img);
          }
        }
        ul.appendChild(li);
      }
      body.appendChild(ul);
    } else if (section.vehicle_types) {
      const ul = document.createElement("ul");
      for (const vt of section.vehicle_types) {
        const li = document.createElement("li");
        li.innerHTML = `<strong>${vt.classification}</strong>: Weight ${vt.total_vehicle_weight}, Payload ${vt.maximum_payload}, Seats ${vt.seating_capacity}, License: ${vt.type_of_license}, Age ${vt.age}`;
        ul.appendChild(li);
      }
      body.appendChild(ul);
    }
    div.appendChild(header);
    div.appendChild(body);
    container.appendChild(div);
  }
}

// --- Stats View ---

function renderStats() {
  const container = document.getElementById("stats-content");
  container.innerHTML = "";

  const progress = getProgress();
  const categories = [
    { label: "All Questions", filter: () => true },
    { label: "Learner's Permit", filter: q => q.source.startsWith("lp") },
    { label: "Driver's License (Standard)", filter: q => q.type === "standard" && q.source.startsWith("dl") },
    { label: "Danger Anticipation", filter: q => q.type === "danger" },
  ];

  // Overall stats
  const overallBuckets = { mastered: 0, in_progress: 0, wrong: 0, unseen: 0 };
  for (const q of allQuestions) {
    overallBuckets[getQuestionStatus(q.id)]++;
  }

  const grid = document.createElement("div");
  grid.className = "stats-grid";
  grid.style.gridTemplateColumns = "1fr 1fr";
  const statItems = [
    ["Mastered", overallBuckets.mastered, "mastered"],
    ["Wrong", overallBuckets.wrong, "wrong"],
    ["Unseen", overallBuckets.unseen, "unseen"],
    ["In Progress", overallBuckets.in_progress, "progress"],
  ];
  for (const [label, count, cls] of statItems) {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `<h3>${label}</h3><div class="stat-number ${cls}">${count}</div>`;
    grid.appendChild(card);
  }
  container.appendChild(grid);

  // Per-category breakdown
  for (const cat of categories) {
    const qs = allQuestions.filter(cat.filter);
    const buckets = { mastered: 0, in_progress: 0, wrong: 0, unseen: 0 };
    for (const q of qs) {
      buckets[getQuestionStatus(q.id)]++;
    }

    const div = document.createElement("div");
    div.className = "stats-category";
    div.innerHTML = `
      <h3>${cat.label} (${qs.length})</h3>
      <div class="stats-row"><span>Mastered</span><span>${buckets.mastered}</span></div>
      <div class="stats-row"><span>In Progress</span><span>${buckets.in_progress}</span></div>
      <div class="stats-row"><span>Wrong</span><span>${buckets.wrong}</span></div>
      <div class="stats-row"><span>Unseen</span><span>${buckets.unseen}</span></div>
    `;
    container.appendChild(div);
  }
}

// --- Reset ---

function resetProgress() {
  if (confirm("Reset all progress? This cannot be undone.")) {
    localStorage.removeItem(STORAGE_KEY);
    sessionHistory = [];
    sessionCount = 0;
    currentQuestion = null;
    dangerQueue = [];
    updateHomeProgress();
    renderStats();
  }
}

// --- Init ---

document.addEventListener("DOMContentLoaded", () => {
  fetchQuestions();

  // Filter buttons
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => applyFilter(btn.dataset.filter));
  });

  // Start button
  document.getElementById("start-btn").addEventListener("click", () => {
    currentQuestion = null;
    sessionCount = 0;
    showView("study");
  });
});
