/*
 * content.js — Injected into the active tab to modify on-page text and visuals.
 *
 * Listens for messages from popup.js to:
 *   1. Collect all page paragraphs and send them to the backend for full reframing
 *   2. Replace each paragraph with its reframed version (preserving direct quotes)
 *   3. Add generation-specific visual overlays
 *   4. Restore the original page
 */

let originalElements = []; // Store originals for undo
let overlayContainer = null;

const API_BASE = "http://localhost:8000";

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "REFRAME_PAGE") {
    // Use async flow but keep the message channel open
    reframePage(request.generation).then((result) => {
      sendResponse(result);
    });
    return true; // Keep message channel open for async response
  }

  if (request.type === "RESTORE_PAGE") {
    restorePage();
    sendResponse({ success: true });
  }
});

async function reframePage(generation) {
  // First restore if already reframed
  restorePage();

  // --- 1. Collect ALL paragraphs from the page ---
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

  // Deduplicate (some selectors may match the same element)
  const seen = new Set();
  paragraphs = paragraphs.filter(el => {
    if (seen.has(el)) return false;
    seen.add(el);
    return el.innerText.trim().length > 15; // Skip tiny fragments
  });

  if (paragraphs.length === 0) {
    // Fallback: grab all <p> on the page
    paragraphs = Array.from(document.querySelectorAll("p"))
      .filter(el => el.innerText.trim().length > 15);
  }

  // Also collect headlines
  const headlineSelectors = "h1, h2, h3, [class*='headline'], [class*='title'], [data-testid*='headline']";
  let headlines = Array.from(document.querySelectorAll(headlineSelectors));
  const seenH = new Set();
  headlines = headlines.filter(el => {
    if (seenH.has(el)) return false;
    seenH.add(el);
    return el.innerText.trim().length > 10;
  });

  // Combine: headlines first, then paragraphs
  const allElements = [...headlines.slice(0, 5), ...paragraphs];
  const allTexts = allElements.map(el => el.innerText.trim());

  if (allTexts.length === 0) {
    return { success: false, error: "No article text found on this page." };
  }

  // Store originals for undo
  allElements.forEach(el => {
    originalElements.push({ element: el, text: el.innerText, html: el.innerHTML });
  });

  // Show loading state
  addModeBanner(generation, true);

  // --- 2. Send to backend for full reframing ---
  try {
    const response = await fetch(`${API_BASE}/api/v1/reframe-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paragraphs: allTexts,
        generation: generation,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      console.error("Reframe API error:", err);
      restorePage();
      return { success: false, error: err.detail?.error?.message || "API error" };
    }

    const data = await response.json();

    // --- 3. Replace each element with its reframed version ---
    data.reframed.forEach((newText, i) => {
      if (i < allElements.length && newText) {
        const el = allElements[i];
        el.innerText = newText;
        el.style.transition = "all 0.3s ease";

        // Generation-specific text styles
        if (generation === "Gen Alpha") {
          el.style.fontFamily = "'Comic Sans MS', cursive";
        } else if (generation === "Boomer") {
          el.style.fontFamily = "Georgia, 'Times New Roman', serif";
          el.style.fontSize = "1.1em";
          el.style.lineHeight = "1.7";
        }
      }
    });

    // --- 4. Update banner to show completion ---
    const banner = document.getElementById("reframe-banner");
    if (banner) {
      banner.remove();
    }
    addModeBanner(generation, false);

    // --- 5. Add visual overlays ---
    if (generation === "Gen Alpha") {
      addBrainrotOverlay();
    } else if (generation === "Boomer") {
      addBoomerOverlay();
    } else if (generation === "Gen Z") {
      addGenZOverlay();
    }

    return { success: true, count: data.count };
  } catch (err) {
    console.error("Reframe failed:", err);
    restorePage();
    return { success: false, error: err.message };
  }
}

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
        font-size: 2rem;
        animation: floatUp 4s ease-in forwards;
        pointer-events: none;
        z-index: 99998;
        opacity: 0.8;
      }
      @keyframes floatUp {
        0% { transform: translateY(100vh) rotate(0deg); opacity: 0.8; }
        100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
      }
      .brainrot-watermark {
        position: fixed;
        bottom: 80px;
        right: 20px;
        font-size: 1.5rem;
        color: rgba(255, 107, 107, 0.6);
        font-family: 'Comic Sans MS', cursive;
        z-index: 99998;
        pointer-events: none;
        animation: pulse 2s infinite;
      }
      @keyframes pulse {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
      }
    </style>
    <div class="brainrot-watermark">🧠💀 brainrot mode activated 💀🧠</div>
  `;
  document.body.appendChild(overlayContainer);

  // Spawn floating emojis
  const emojis = ["💀", "🗿", "🧠", "😭", "🔥", "💅", "✨", "🤡", "👁️", "⚡"];
  for (let i = 0; i < 12; i++) {
    setTimeout(() => {
      if (!overlayContainer) return;
      const emojiEl = document.createElement("span");
      emojiEl.className = "brainrot-emoji";
      emojiEl.textContent = emojis[Math.floor(Math.random() * emojis.length)];
      emojiEl.style.left = Math.random() * 90 + "%";
      emojiEl.style.animationDuration = (3 + Math.random() * 3) + "s";
      emojiEl.style.animationDelay = (Math.random() * 0.5) + "s";
      overlayContainer.appendChild(emojiEl);
      setTimeout(() => emojiEl.remove(), 7000);
    }, i * 500);
  }
}

function addGenZOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .genz-vibe {
        position: fixed;
        bottom: 80px;
        right: 20px;
        font-size: 1.2rem;
        color: rgba(129, 140, 248, 0.7);
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        z-index: 99998;
        pointer-events: none;
        animation: fadeInOut 3s infinite;
      }
      @keyframes fadeInOut {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.8; }
      }
    </style>
    <div class="genz-vibe">✨ it's giving reframed ✨</div>
  `;
  document.body.appendChild(overlayContainer);
}

function addBoomerOverlay() {
  overlayContainer = document.createElement("div");
  overlayContainer.id = "reframe-overlay";
  overlayContainer.innerHTML = `
    <style>
      .boomer-notice {
        position: fixed;
        bottom: 80px;
        right: 20px;
        background: #1a365d;
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 1rem;
        z-index: 99998;
        pointer-events: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      }
    </style>
    <div class="boomer-notice">📰 ENHANCED READABILITY MODE ACTIVE</div>
  `;
  document.body.appendChild(overlayContainer);

  document.body.style.fontSize = "1.15em";
  document.body.style.lineHeight = "1.8";
}

function addModeBanner(generation, isLoading = false) {
  const colors = {
    "Gen Alpha": { bg: "#ff6b6b", text: "🧠 BRAINROT MODE", loadText: "🧠 Reframing page with brainrot..." },
    "Gen Z": { bg: "#818cf8", text: "✨ GEN Z MODE", loadText: "✨ Reframing page for Gen Z..." },
    "Millennial": { bg: "#f59e0b", text: "💅 MILLENNIAL MODE", loadText: "💅 Reframing page for Millennials..." },
    "Gen X": { bg: "#6b7280", text: "🤷 GEN X MODE", loadText: "🤷 Reframing page for Gen X..." },
    "Boomer": { bg: "#1a365d", text: "📰 BOOMER MODE", loadText: "📰 Reframing page for Boomers..." },
  };

  const config = colors[generation] || { bg: "#333", text: "REFRAMED", loadText: "Reframing..." };

  const banner = document.createElement("div");
  banner.id = "reframe-banner";
  banner.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    padding: 8px;
    background: ${config.bg};
    color: white;
    text-align: center;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    font-weight: 600;
    z-index: 99999;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    letter-spacing: 1px;
    transition: all 0.3s ease;
  `;
  banner.textContent = isLoading ? config.loadText : config.text;
  document.body.appendChild(banner);
  document.body.style.marginTop = "36px";
}

function restorePage() {
  // Restore original text and styles
  originalElements.forEach(({ element, html }) => {
    element.innerHTML = html;
    element.style.color = "";
    element.style.textShadow = "";
    element.style.fontSize = "";
    element.style.fontWeight = "";
    element.style.letterSpacing = "";
    element.style.fontFamily = "";
    element.style.lineHeight = "";
  });
  originalElements = [];

  // Remove overlays
  const overlay = document.getElementById("reframe-overlay");
  if (overlay) overlay.remove();
  overlayContainer = null;

  // Remove banner
  const banner = document.getElementById("reframe-banner");
  if (banner) banner.remove();

  // Reset body styles
  document.body.style.marginTop = "";
  document.body.style.fontSize = "";
  document.body.style.lineHeight = "";
}
