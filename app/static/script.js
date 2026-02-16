
const ingestBtn = document.getElementById("ingestBtn");
const askBtn = document.getElementById("askBtn");
const toggleSitesBtn = document.getElementById("toggleSitesBtn");
const clearBtn = document.getElementById("clearBtn");

const textUrls = document.getElementById("urlsText");
const textAsk = document.getElementById("askText");

const ingestOut = document.getElementById("ingestOut");
const answerOut = document.getElementById("answerOut");
const tokensUsed = document.getElementById("tokensUsed");

const modelsSelect = document.getElementById("modelsList");
const ingestedSitesList = document.getElementById("ingestedSitesList");

const ingestForm = document.getElementById("ingestForm");
const sitesView = document.getElementById("sitesView");
const sitesCount = document.getElementById("sitesCount");
const sitesStatus = document.getElementById("sitesStatus");

var showSitesList = false;

var models = [];
var selected_model_id = null;

textAsk.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    askBtn.click();
  }
});

textUrls.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    ingestBtn.click();
  }
});

// Set session id
let sessionId = null;
try {
  sessionId = localStorage.getItem("sessionId") || null;
} catch { }

// Get the all models
initState();

// Handle ingest view toggle
toggleSitesBtn.onclick = () => {
  setSitesView(!showSitesList);
};

// Handle ingest button click
ingestBtn.onclick = async () => {
  await ingestSites();
};

// Handle ask button click
askBtn.onclick = async () => {
  await handleAsk();
};

// Handle clear button click
clearBtn.onclick = async () => {
  await clearSites();
};

modelsSelect.onchange = async (_e) => {
  selected_model_id = modelsSelect.value;
}

async function readBody(res) {
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/json")) return await res.json();
  return await res.text();
}

async function ingestSites() {
  ingestOut.textContent = "Ingesting...";

  const urls = textUrls
    .value.split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);

  let res;
  try {
    res = await fetch("/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });
  } catch (e) {
    ingestOut.textContent = String(e);
    return;
  }

  const body = await readBody(res);
  console.log(body)
  ingestOut.textContent = JSON.stringify(body, null, 2);

  if (res.ok) {
    getIngestedSites();
  }
}

async function handleAsk() {
  answerOut.textContent = "Thinking...";
  tokensUsed.textContent = "Tokens used: - | Total: -";
  const question = textAsk.value;

  const res = await fetch("/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: question,
      session_id: sessionId,
      model: selected_model_id,
    }),
  }).catch((e) => {
    ingestOut.textContent = String(e);
    return;
  });

  const body = await readBody(res);
  if (!res.ok) {
    answerOut.textContent = JSON.stringify(body, null, 2);
    return;
  }
  console.log(body)

  tokensUsed.textContent = `Tokens used: ${body.tokens} | Total: ${body.tokens_used_total}`;

  let out = body.answer;
  if (body.session_id) {
    sessionId = body.session_id;
    localStorage.setItem("sessionId", sessionId)
  }

  if (body.sources) {
    out += "\n\nSources:\n"
    let i = 1;
    for (const s of body.sources) {
      out += `[${i}] ${s}\n`;
      i++;
    }
  }
  answerOut.textContent = out;
}

async function initState() {
  const res = await fetch("/getState", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  }).catch((e) => {
    console.log(e);
    return;
  });
  const body = await readBody(res);
  console.log(body)

  const models_list = body.models;
  selected_model_id = body.model_id;

  // Initialize models list
  models_list.forEach(function(model, _i) {
    models.push({ "id": model.id, "provider": "openai" })
    var opt = document.createElement("option");
    opt.value = model.id;
    opt.textContent = model.id;
    if (selected_model_id == model.id) {
      opt.selected = true;
    }
    modelsSelect.appendChild(opt);
  });
}

function setSitesView(show) {
  showSitesList = Boolean(show);
  ingestForm.hidden = showSitesList;
  sitesView.hidden = !showSitesList;
  toggleSitesBtn.textContent = showSitesList ? "Back" : "View sites";

  getIngestedSites();
}

async function getIngestedSites() {
  ingestedSitesList.textContent = "";
  sitesStatus.textContent = "Loading...";

  let res;
  try {
    res = await fetch("/sites", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.log(e);
    sitesStatus.textContent = `Failed to load sites: ${String(e)}`;
    return;
  }

  const body = await readBody(res);
  const sites_list = body.sites;

  if (!res.ok) {
    sitesStatus.textContent = `Failed to load sites: ${typeof body === "string"
      ? body : JSON.stringify(body)}`;
    sitesCount.textContent = "";
    return;
  }

  sites_list.forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    ingestedSitesList.appendChild(li);
  });

  sitesCount.textContent = `Sites: ${sites_list.length}`;
  sitesStatus.textContent = sites_list.length ? "" : "No sites ingested.";
}

async function clearSites() {
  let res;
  try {
    res = await fetch("/clear", { method: "POST" });
  } catch (e) {
    console.log(e);
    sitesStatus.textContent = `Failed to clear sites: ${String(e)}`;
    return;
  }
  await getIngestedSites();
}
