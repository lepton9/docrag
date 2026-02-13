
const ingestBtn = document.getElementById("ingestBtn");
const askBtn = document.getElementById("askBtn");

const textUrls = document.getElementById("urlsText");
const textAsk = document.getElementById("askText");

const ingestOut = document.getElementById("ingestOut");
const answerOut = document.getElementById("answerOut");
const tokensUsed = document.getElementById("tokensUsed");

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

// Handle ingest button click
ingestBtn.onclick = async () => {
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
};

// Handle ask button click
askBtn.onclick = async () => {
  answerOut.textContent = "Thinking...";
  tokensUsed.textContent = "Tokens used: - | Total: -";
  const question = textAsk.value;

  const res = await fetch("/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: question,
      session_id: sessionId,
      model: null,
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
};

async function readBody(res) {
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/json")) return await res.json();
  return await res.text();
}
