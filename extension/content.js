/*
 * content.js — Injected into the active tab to modify on-page text and visuals.
 */

let originalElements = []; // Store originals for undo
let overlayContainer = null;

// Persistent reframe cache via chrome.storage.local
async function getCachedReframe(key) {
  return new Promise(resolve => {
    chrome.storage.local.get(key, result => resolve(result[key] || null));
  });
}
async function setCachedReframe(key, data) {
  return new Promise(resolve => {
    chrome.storage.local.set({ [key]: data }, resolve);
  });
}

const API_BASE = "http://localhost:8000";

// Lowercase helper (preserves quoted text)
function lowercaseExceptQuotes(text) {
  return text.replace(/(".*?"|'.*?')|([^"']+)/g, (match, quoted, outside) => {
    return quoted ? quoted : outside.toLowerCase();
  });
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "REFRAME_PAGE") {
    reframePage(request.generation).then((result) => sendResponse(result));
    return true;
  }

  if (request.type === "RESTORE_PAGE") {
    restorePage();
    sendResponse({ success: true });
  }
});

async function reframePage(generation) {
  restorePage();

  const selectors = [
    "article p",
    "[class*='article'] p",
    "[class*='story'] p",
    "[class*='content'] p",
    "main p",
    ".post-body p",
    "#article-body p",
  ].join(", ");

  let paragraphs = Array.from(document.querySelectorAll(selectors));

  const seen = new Set();
  paragraphs = paragraphs.filter(el => {
    if (seen.has(el)) return false;
    seen.add(el);
    return el.innerText.trim().length > 15;
  });

  if (paragraphs.length === 0) {
    paragraphs = Array.from(document.querySelectorAll("p"))
      .filter(el => el.innerText.trim().length > 15);
  }

  const headlineSelectors = "h1, h2, h3, [class*='headline'], [class*='title'], [data-testid*='headline']";
  let headlines = Array.from(document.querySelectorAll(headlineSelectors));
  const seenH = new Set();
  headlines = headlines.filter(el => {
    if (seenH.has(el)) return false;
    seenH.add(el);
    return el.innerText.trim().length > 10;
  });

  const allElements = [...headlines.slice(0, 5), ...paragraphs];
  const allTexts = allElements.map(el => el.innerText.trim());

  if (allTexts.length === 0) {
    return { success: false, error: "No article text found on this page." };
  }

  allElements.forEach(el => {
    originalElements.push({ element: el, text: el.innerText, html: el.innerHTML });
  });

  const cacheKey = `reframe_${window.location.href}||${generation}`;
  const cachedResult = await getCachedReframe(cacheKey);

  if (cachedResult && cachedResult.length === allElements.length) {
    addModeBanner(generation, false);
    cachedResult.forEach((newText, i) => {
      if (i < allElements.length && newText) {
        const el = allElements[i];
        if (generation === "Gen Z") newText = lowercaseExceptQuotes(newText);
        el.innerText = newText;
        el.style.transition = "all 0.3s ease";
        applyElementStyle(el, generation);
      }
    });
    addGenerationOverlay(generation);
    return { success: true, count: cachedResult.length, cached: true };
  }

  addModeBanner(generation, true);

  try {
    const response = await fetch(`${API_BASE}/api/v1/reframe-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paragraphs: allTexts, generation }),
    });

    if (!response.ok) {
      restorePage();
      return { success: false, error: "API error" };
    }

    const data = await response.json();

    data.reframed.forEach((newText, i) => {
      if (i < allElements.length && newText) {
        const el = allElements[i];
        if (generation === "Gen Z") newText = lowercaseExceptQuotes(newText);
        el.innerText = newText;
        el.style.transition = "all 0.3s ease";
        applyElementStyle(el, generation);
      }
    });

    await setCachedReframe(cacheKey, data.reframed);

    const banner = document.getElementById("reframe-banner");
    if (banner) banner.remove();
    addModeBanner(generation, false);
    addGenerationOverlay(generation);

    return { success: true, count: data.count };
  } catch (err) {
    restorePage();
    return { success: false, error: err.message };
  }
}

// ============================================================
// HELPER FUNCTIONS — Per-element styling & overlay dispatch
// ============================================================

function applyElementStyle(el, generation) {
  switch (generation) {
    case "Gen Alpha":
      el.style.fontFamily = "'Comic Sans MS', cursive";
      break;
    case "Gen Z":
      el.style.fontFamily = "-apple-system, BlinkMacSystemFont, sans-serif";
      el.style.letterSpacing = "0.3px";
      break;
    case "Millennial":
      el.style.fontFamily = "'Avenir', 'Segoe UI', sans-serif";
      break;
    case "Gen X":
      el.style.fontFamily = "'Courier New', monospace";
      el.style.color = "#333";
      break;
    case "Boomer":
      el.style.fontFamily = "Georgia, 'Times New Roman', serif";
      el.style.fontSize = "1.15em";
      el.style.lineHeight = "1.8";
      break;
  }
}

function addGenerationOverlay(generation) {
  switch (generation) {
    case "Gen Alpha": addBrainrotOverlay(); break;
    case "Gen Z": addGenZOverlay(); break;
    case "Millennial": addMillennialOverlay(); break;
    case "Gen X": addGenXOverlay(); break;
    case "Boomer": addBoomerOverlay(); break;
  }
}

// ============================================================
// GENERATION OVERLAY FUNCTIONS — Visual magic per generation
// ============================================================

function addBrainrotOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      #reframe-overlay {
        pointer-events: none;
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        z-index: 99998;
        overflow: hidden;
      }
      .brainrot-emoji {
        position: fixed;
        font-size: 2.5rem;
        animation: brainrotFloat 5s ease-in forwards;
        pointer-events: none;
        z-index: 99998;
        filter: drop-shadow(0 0 6px rgba(255,100,100,0.5));
      }
      @keyframes brainrotFloat {
        0% { transform: translateY(110vh) rotate(0deg) scale(0.5); opacity: 0.9; }
        50% { transform: translateY(50vh) rotate(180deg) scale(1.2); opacity: 1; }
        100% { transform: translateY(-80px) rotate(360deg) scale(0.3); opacity: 0; }
      }
      .brainrot-watermark {
        position: fixed;
        bottom: 50%;
        left: 50%;
        transform: translate(-50%, 50%);
        font-size: 2rem;
        font-family: 'Comic Sans MS', cursive;
        z-index: 99998;
        pointer-events: none;
        text-align: center;
        animation: brainrotPulse 1.5s ease-in-out infinite, rainbowText 3s linear infinite;
        text-shadow: 0 0 20px rgba(255,50,50,0.6), 0 0 40px rgba(255,150,0,0.4);
      }
      @keyframes brainrotPulse {
        0%, 100% { opacity: 0.6; transform: translate(-50%, 50%) scale(1) rotate(-2deg); }
        50% { opacity: 1; transform: translate(-50%, 50%) scale(1.1) rotate(2deg); }
      }
      @keyframes rainbowText {
        0% { color: #ff6b6b; }
        16% { color: #ffa500; }
        33% { color: #ffd93d; }
        50% { color: #6bcb77; }
        66% { color: #4d96ff; }
        83% { color: #9b59b6; }
        100% { color: #ff6b6b; }
      }
      .brainrot-corner {
        position: fixed;
        font-size: 3rem;
        z-index: 99998;
        pointer-events: none;
        animation: cornerBounce 2s ease-in-out infinite;
      }
      @keyframes cornerBounce {
        0%, 100% { transform: scale(1) rotate(0deg); }
        50% { transform: scale(1.3) rotate(15deg); }
      }
    </style>
    <div class="brainrot-watermark">🧠💀 brainrot mode activated 💀🧠</div>
    <div class="brainrot-corner" style="top:60px;left:15px;animation-delay:0s;">💀</div>
    <div class="brainrot-corner" style="top:60px;right:15px;animation-delay:0.3s;">🗿</div>
    <div class="brainrot-corner" style="bottom:15px;left:15px;animation-delay:0.6s;">🧠</div>
    <div class="brainrot-corner" style="bottom:15px;right:15px;animation-delay:0.9s;">😭</div>
  `;
  document.body.appendChild(overlayContainer);

  // Spawn continuous floating emojis
  const emojis = ["💀", "🗿", "🧠", "😭", "🔥", "💅", "✨", "🤡", "👁️", "⚡", "🥶", "😤", "👀", "🫡", "🦴"];
  let spawnCount = 0;
  const spawnInterval = setInterval(() => {
    if (!overlayContainer || spawnCount > 30) { clearInterval(spawnInterval); return; }
    const emojiEl = document.createElement("span");
    emojiEl.className = "brainrot-emoji";
    emojiEl.textContent = emojis[Math.floor(Math.random() * emojis.length)];
    emojiEl.style.left = Math.random() * 95 + "%";
    emojiEl.style.animationDuration = (3 + Math.random() * 4) + "s";
    emojiEl.style.animationDelay = (Math.random() * 0.3) + "s";
    emojiEl.style.fontSize = (1.5 + Math.random() * 2) + "rem";
    overlayContainer.appendChild(emojiEl);
    setTimeout(() => emojiEl.remove(), 8000);
    spawnCount++;
  }, 400);
}

function addGenZOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .genz-vibe-container {
        position: fixed;
        bottom: 0; left: 0; width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 12px;
        z-index: 99998;
        pointer-events: none;
      }
      .genz-vibe {
        font-size: 1.1rem;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif;
        z-index: 99998;
        pointer-events: none;
        text-align: center;
        padding: 10px 24px;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(129,140,248,0.15), rgba(236,72,153,0.15));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(129,140,248,0.3);
        color: rgba(129, 140, 248, 0.9);
        animation: genzFloat 3s ease-in-out infinite;
        letter-spacing: 0.5px;
      }
      @keyframes genzFloat {
        0%, 100% { opacity: 0.7; transform: translateY(0); }
        50% { opacity: 1; transform: translateY(-5px); }
      }
      .genz-sparkle {
        position: fixed;
        font-size: 1rem;
        pointer-events: none;
        z-index: 99998;
        animation: genzSparkle 2s ease-in-out infinite;
      }
      @keyframes genzSparkle {
        0%, 100% { opacity: 0; transform: scale(0.5); }
        50% { opacity: 0.8; transform: scale(1.2); }
      }
    </style>
    <div class="genz-vibe-container">
      <div class="genz-vibe">✨ it's giving reframed ✨</div>
    </div>
    <div class="genz-sparkle" style="top:20%;left:10%;animation-delay:0s;">✨</div>
    <div class="genz-sparkle" style="top:40%;right:8%;animation-delay:0.5s;">💫</div>
    <div class="genz-sparkle" style="bottom:30%;left:15%;animation-delay:1s;">✨</div>
    <div class="genz-sparkle" style="top:60%;right:20%;animation-delay:1.5s;">💫</div>
  `;
  document.body.appendChild(overlayContainer);
}

function addMillennialOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .mill-banner-container {
        position: fixed;
        bottom: 0; left: 0; width: 100%;
        display: flex;
        justify-content: center;
        padding: 12px;
        z-index: 99998;
        pointer-events: none;
      }
      .mill-banner {
        text-align: center;
        padding: 10px 28px;
        border-radius: 24px;
        background: linear-gradient(135deg, #f8b4c8, #ffecd2);
        color: #7c3a5e;
        font-family: 'Avenir', 'Segoe UI', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        pointer-events: none;
        box-shadow: 0 4px 15px rgba(248,180,200,0.4);
        animation: millPulse 3s ease-in-out infinite;
        letter-spacing: 0.5px;
      }
      @keyframes millPulse {
        0%, 100% { box-shadow: 0 4px 15px rgba(248,180,200,0.3); transform: scale(1); }
        50% { box-shadow: 0 4px 25px rgba(248,180,200,0.6); transform: scale(1.02); }
      }
      .mill-hashtag {
        position: fixed;
        font-family: 'Avenir', sans-serif;
        font-size: 0.85rem;
        color: rgba(124, 58, 94, 0.35);
        pointer-events: none;
        z-index: 99998;
        animation: hashtagDrift 4s ease-in-out infinite;
      }
      @keyframes hashtagDrift {
        0%, 100% { opacity: 0.2; transform: translateY(0) rotate(-3deg); }
        50% { opacity: 0.5; transform: translateY(-8px) rotate(3deg); }
      }
    </style>
    <div class="mill-banner-container">
      <div class="mill-banner">💅 #adulting #reframed #blessed 💅</div>
    </div>
    <div class="mill-hashtag" style="top:25%;left:5%;animation-delay:0s;">#goals</div>
    <div class="mill-hashtag" style="top:45%;right:5%;animation-delay:0.7s;">#relatable</div>
    <div class="mill-hashtag" style="bottom:35%;left:8%;animation-delay:1.4s;">#FOMO</div>
    <div class="mill-hashtag" style="top:15%;right:12%;animation-delay:2.1s;">#vibes</div>
  `;
  document.body.appendChild(overlayContainer);
}

function addGenXOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .genx-badge-container {
        position: fixed;
        bottom: 0; left: 0; width: 100%;
        display: flex;
        justify-content: center;
        padding: 12px;
        z-index: 99998;
        pointer-events: none;
      }
      .genx-badge {
        text-align: center;
        padding: 8px 20px;
        border-radius: 4px;
        background: rgba(50,50,50,0.85);
        color: #a0a0a0;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        pointer-events: none;
        border: 1px solid #555;
        letter-spacing: 1px;
      }
    </style>
    <div class="genx-badge-container">
      <div class="genx-badge">🤷 whatever — it is what it is 🤷</div>
    </div>
  `;
  document.body.appendChild(overlayContainer);
}

function addBoomerOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .boomer-notice-container {
        position: fixed;
        bottom: 0; left: 0; width: 100%;
        display: flex;
        justify-content: center;
        padding: 12px;
        z-index: 99998;
        pointer-events: none;
      }
      .boomer-notice {
        text-align: center;
        background: linear-gradient(180deg, #1a365d, #0f2440);
        color: #e8d5a3;
        padding: 12px 28px;
        border-radius: 2px;
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 1rem;
        font-weight: bold;
        pointer-events: none;
        box-shadow: 0 2px 12px rgba(0,0,0,0.4);
        border: 2px solid #c9a84c;
        letter-spacing: 2px;
        text-transform: uppercase;
      }
    </style>
    <div class="boomer-notice-container">
      <div class="boomer-notice">📰 ENHANCED READABILITY MODE ACTIVE 📰</div>
    </div>
  `;
  document.body.appendChild(overlayContainer);

  document.body.style.fontSize = "1.15em";
  document.body.style.lineHeight = "1.8";
}

// ============================================================
// MODE BANNER — Themed per generation
// ============================================================

function addModeBanner(generation, isLoading = false) {
  const themes = {
    "Gen Alpha": { bg: "linear-gradient(90deg, #ff6b6b, #ffa500, #ffd93d, #6bcb77, #4d96ff, #9b59b6)", color: "#fff", text: "🧠💀 BRAINROT MODE 💀🧠", loadText: "🧠 rotting the page rn... 💀", font: "'Comic Sans MS', cursive" },
    "Gen Z": { bg: "linear-gradient(135deg, #818cf8, #ec4899)", color: "#fff", text: "✨ gen z mode ✨", loadText: "✨ reframing bestie... ✨", font: "-apple-system, sans-serif" },
    "Millennial": { bg: "linear-gradient(135deg, #f8b4c8, #ffecd2)", color: "#7c3a5e", text: "💅 MILLENNIAL MODE 💅", loadText: "💅 #reframing #loading #blessed...", font: "'Avenir', 'Segoe UI', sans-serif" },
    "Gen X": { bg: "#333", color: "#a0a0a0", text: "🤷 Gen X Mode — whatever", loadText: "🤷 Reframing... or not...", font: "'Courier New', monospace" },
    "Boomer": { bg: "linear-gradient(180deg, #1a365d, #0f2440)", color: "#e8d5a3", text: "📰 BOOMER MODE — ENHANCED READABILITY 📰", loadText: "📰 LOADING ENHANCED READABILITY...", font: "Georgia, 'Times New Roman', serif" },
  };

  const theme = themes[generation] || { bg: "#333", color: "#fff", text: `${generation} MODE`, loadText: "Reframing page...", font: "sans-serif" };

  const banner = document.createElement("div");
  banner.id = "reframe-banner";
  banner.style.cssText = `
    position: fixed;
    top: 0; left: 0; width: 100%;
    padding: 10px 16px;
    background: ${theme.bg};
    color: ${theme.color};
    text-align: center;
    font-family: ${theme.font};
    font-size: 14px;
    font-weight: 700;
    z-index: 99999;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    letter-spacing: 1px;
    transition: all 0.3s ease;
    ${generation === "Gen Alpha" ? "background-size: 300% 100%; animation: bannerRainbow 3s linear infinite;" : ""}
  `;
  banner.textContent = isLoading ? theme.loadText : theme.text;

  // Add rainbow animation keyframes for Gen Alpha
  if (generation === "Gen Alpha") {
    const style = document.createElement("style");
    style.id = "reframe-banner-style";
    style.textContent = `@keyframes bannerRainbow { 0% { background-position: 0% 50%; } 100% { background-position: 300% 50%; } }`;
    document.head.appendChild(style);
  }

  document.body.appendChild(banner);
  document.body.style.marginTop = "40px";
}

// ============================================================
// RESTORE — Clean up everything
// ============================================================

function restorePage() {
  originalElements.forEach(({ element, html }) => {
    element.innerHTML = html;
    element.style.fontFamily = "";
    element.style.fontSize = "";
    element.style.lineHeight = "";
    element.style.color = "";
    element.style.textShadow = "";
    element.style.letterSpacing = "";
  });
  originalElements = [];

  const overlay = document.getElementById("reframe-overlay");
  if (overlay) overlay.remove();
  overlayContainer = null;

  const banner = document.getElementById("reframe-banner");
  if (banner) banner.remove();

  const bannerStyle = document.getElementById("reframe-banner-style");
  if (bannerStyle) bannerStyle.remove();

  document.body.style.marginTop = "";
  document.body.style.fontSize = "";
  document.body.style.lineHeight = "";
  document.documentElement.style.fontSize = "";
}