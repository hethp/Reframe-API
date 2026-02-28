/*
 * content.js — Injected into the active tab to modify on-page text and visuals.
 *
 * Listens for messages from popup.js to:
 *   1. Replace headlines/paragraphs with generational translations
 *   2. Add brainrot overlays for Gen Alpha mode
 *   3. Restore the original page
 */

let originalElements = []; // Store originals for undo
let overlayContainer = null;

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "REFRAME_PAGE") {
        reframePage(request.generation, request.translations, request.summary);
        sendResponse({ success: true });
    }

    if (request.type === "RESTORE_PAGE") {
        restorePage();
        sendResponse({ success: true });
    }
});

function reframePage(generation, translations, summary) {
    // First restore if already reframed
    restorePage();

    const translatedText = translations[generation] || summary;

    // --- 1. Replace Headlines ---
    const headlineSelectors = "h1, h2, h3, [class*='headline'], [class*='title'], [data-testid*='headline']";
    const headlines = document.querySelectorAll(headlineSelectors);

    headlines.forEach((el, i) => {
        if (el.innerText.trim().length > 10 && i < 5) {
            originalElements.push({ element: el, text: el.innerText, html: el.innerHTML });
            // Use a portion of the translated text for the headline
            const headlineText = translatedText.split('.')[0] || translatedText;
            el.innerText = headlineText;
            el.style.transition = "all 0.3s ease";

            if (generation === "Gen Alpha") {
                el.style.color = "#ff6b6b";
                el.style.textShadow = "0 0 10px rgba(255, 107, 107, 0.5)";
            } else if (generation === "Boomer") {
                el.style.fontSize = "1.4em";
                el.style.fontWeight = "bold";
                el.style.letterSpacing = "0.5px";
            }
        }
    });

    // --- 2. Replace Article Body Paragraphs ---
    const paragraphs = document.querySelectorAll("article p, [class*='article'] p, [class*='story'] p, main p");
    const sentences = translatedText.split(/(?<=[.!?])\s+/);

    paragraphs.forEach((el, i) => {
        if (el.innerText.trim().length > 20 && i < 10) {
            originalElements.push({ element: el, text: el.innerText, html: el.innerHTML });
            el.innerText = sentences[i % sentences.length] || translatedText;
            el.style.transition = "all 0.3s ease";
        }
    });

    // --- 3. Generation-specific Visual Overlays ---
    if (generation === "Gen Alpha") {
        addBrainrotOverlay();
    } else if (generation === "Boomer") {
        addBoomerOverlay();
    } else if (generation === "Gen Z") {
        addGenZOverlay();
    }

    // --- 4. Banner showing which mode is active ---
    addModeBanner(generation);
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
            // Clean up after animation
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

    // Increase font size globally for boomer mode
    document.body.style.fontSize = "1.15em";
    document.body.style.lineHeight = "1.8";
}

function addModeBanner(generation) {
    const colors = {
        "Gen Alpha": { bg: "#ff6b6b", text: "🧠 BRAINROT MODE" },
        "Gen Z": { bg: "#818cf8", text: "✨ GEN Z MODE" },
        "Millennial": { bg: "#f59e0b", text: "💅 MILLENNIAL MODE" },
        "Gen X": { bg: "#6b7280", text: "🤷 GEN X MODE" },
        "Boomer": { bg: "#1a365d", text: "📰 BOOMER MODE" },
    };

    const config = colors[generation] || { bg: "#333", text: "REFRAMED" };

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
    banner.textContent = config.text;
    document.body.appendChild(banner);

    // Push page content down
    document.body.style.marginTop = "36px";
}

function restorePage() {
    // Restore original text
    originalElements.forEach(({ element, html }) => {
        element.innerHTML = html;
        element.style.color = "";
        element.style.textShadow = "";
        element.style.fontSize = "";
        element.style.fontWeight = "";
        element.style.letterSpacing = "";
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
