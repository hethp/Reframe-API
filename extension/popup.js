let currentAnalysis = null;
let currentUrl = "";

document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const analyzeBtn = document.getElementById('analyze-btn');
    const startState = document.getElementById('start-state');
    const loadingState = document.getElementById('loading');
    const contentState = document.getElementById('content');
    const errorState = document.getElementById('error');
    const container = document.querySelector(".container");
    const closeBtn = document.getElementById('close-sidebar');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            // if loaded in an injected iframe, close the sidebar by removing parent div
            if (window.top && window.top.document) {
                const sidebar = window.top.document.getElementById('reframe-sidebar');
                if (sidebar) sidebar.remove();
            }
        });
    }

    const biasMarker = document.getElementById('bias-marker');
    const biasLabel = document.getElementById('bias-label');
    const biasExplanation = document.getElementById('bias-explanation');

    const generationSelect = document.getElementById('generation-select');
    const summaryText = document.getElementById('summary-text');

    const chatInput = document.getElementById('chat-input');
    const chatSubmit = document.getElementById('chat-submit');
    const chatHistory = document.getElementById('chat-history');

    // --- 1. Analysis Logic ---
    analyzeBtn.addEventListener('click', async () => {
        let tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) return;
        currentUrl = tabs[0].url;

        startState.classList.add('hidden');
        errorState.classList.add('hidden');
        loadingState.classList.remove('hidden');

        chrome.runtime.sendMessage(
            { type: "PROCESS_NEWS", url: currentUrl },
            (response) => {
                loadingState.classList.add('hidden');
                if (response && response.success) {
                    currentAnalysis = response.data.data;
                    displayAnalysis(currentAnalysis);
                    contentState.classList.remove('hidden');
                } else {
                    errorState.textContent = "Error: " + (response ? response.error : "Failed to connect to backend");
                    errorState.classList.remove('hidden');
                    startState.classList.remove('hidden');
                }
            }
        );
    });

    function displayAnalysis(data) {
        // Set Bias Marker Position
        const score = data.bias.score; // -100 to 100
        const percentage = ((score + 100) / 200) * 100;
        biasMarker.style.left = `${percentage}%`;
        biasLabel.textContent = `${data.bias.label} (${score})`;
        biasExplanation.textContent = data.bias.explanation;

        // Set Default Summary
        summaryText.textContent = data.summary;
        generationSelect.value = "summary";
        container.classList.remove("boomer-mode"); // Reset boomer mode on new analysis
        restoreBtn.classList.add('hidden');
        reframeBtn.classList.remove('hidden');
    }

    // --- 2. Translation & Boomer Mode Logic ---
    const reframeBtn = document.getElementById('reframe-page-btn');
    const restoreBtn = document.getElementById('restore-page-btn');

    generationSelect.addEventListener('change', (e) => {
        const val = e.target.value;

        // Handle Boomer Mode UI Scaling
        if (val === "Boomer") {
            container.classList.add("boomer-mode");
        } else {
            container.classList.remove("boomer-mode");
        }

        // Handle Text Content Change
        summaryText.classList.remove('fade-in');
        void summaryText.offsetWidth; // trigger reflow for animation

        if (val === "summary") {
            summaryText.textContent = currentAnalysis.summary;
        } else {
            // Checks if translation exists, fallback to summary if not
            let translation = currentAnalysis.translations[val] || currentAnalysis.summary;
            // Safety: if the LLM returned an object instead of a string, flatten it
            if (typeof translation === 'object' && translation !== null) {
                translation = Object.values(translation).join(' ');
            }
            summaryText.textContent = translation;
        }

        summaryText.classList.add('fade-in');
    });

    // --- Reframe Page Button ---
    reframeBtn.addEventListener('click', async () => {
        if (!currentAnalysis) return;

        const generation = generationSelect.value;
        if (generation === "summary") {
            alert("Select a generation style first!");
            return;
        }

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) return;

        chrome.tabs.sendMessage(tab.id, {
            type: "REFRAME_PAGE",
            generation: generation,
            translations: currentAnalysis.translations,
            summary: currentAnalysis.summary,
        });

        reframeBtn.classList.add('hidden');
        restoreBtn.classList.remove('hidden');
    });

    // --- Restore Page Button ---
    restoreBtn.addEventListener('click', async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) return;

        chrome.tabs.sendMessage(tab.id, { type: "RESTORE_PAGE" });

        restoreBtn.classList.add('hidden');
        reframeBtn.classList.remove('hidden');
    });

    // --- 3. Chat Logic ---
    chatSubmit.addEventListener('click', sendChat);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChat();
    });

    function sendChat() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendChat(text, 'user');
        chatInput.value = '';

        const loadingId = 'loading-' + Date.now();
        appendChat('...', 'ai', loadingId);

        chrome.runtime.sendMessage(
            { type: "CHAT", url: currentUrl, message: text },
            (response) => {
                const loader = document.getElementById(loadingId);
                if (loader) loader.remove();

                if (response && response.success && response.data.reply) {
                    appendChat(response.data.reply, 'ai');
                } else {
                    appendChat('Error analyzing response', 'ai');
                }
            }
        );
    }

    function appendChat(message, sender, id = null) {
        const div = document.createElement('div');
        div.className = `chat-bubble ${sender}`;
        div.textContent = message;
        if (id) div.id = id;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});