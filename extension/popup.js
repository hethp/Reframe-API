let currentAnalysis = null;
let currentUrl = "";

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const startState = document.getElementById('start-state');
    const loadingState = document.getElementById('loading');
    const contentState = document.getElementById('content');
    const errorState = document.getElementById('error');

    const biasMarker = document.getElementById('bias-marker');
    const biasLabel = document.getElementById('bias-label');
    const biasExplanation = document.getElementById('bias-explanation');

    const generationSelect = document.getElementById('generation-select');
    const summaryText = document.getElementById('summary-text');

    const chatInput = document.getElementById('chat-input');
    const chatSubmit = document.getElementById('chat-submit');
    const chatHistory = document.getElementById('chat-history');

    analyzeBtn.addEventListener('click', async () => {
        // Get current tab URL
        let tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) return;
        currentUrl = tabs[0].url;

        // Show loading
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
        // Set Bias
        const score = data.bias.score; // -100 to 100
        // map -100 to 100 into 0% to 100%
        const percentage = ((score + 100) / 200) * 100;
        biasMarker.style.left = `${percentage}%`;
        biasLabel.textContent = `${data.bias.label} (${score})`;
        biasExplanation.textContent = data.bias.explanation;

        // Set Summary initially
        summaryText.textContent = data.summary;
        generationSelect.value = "summary";
    }

    generationSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        summaryText.classList.remove('fade-in');

        // trigger reflow
        void summaryText.offsetWidth;

        if (val === "summary") {
            summaryText.textContent = currentAnalysis.summary;
        } else {
            summaryText.textContent = currentAnalysis.translations[val];
        }

        summaryText.classList.add('fade-in');
    });

    // Chat logic
    chatSubmit.addEventListener('click', sendChat);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChat();
    });

    function sendChat() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendChat(text, 'user');
        chatInput.value = '';

        // Add loading indicator
        const loadingId = 'loading-' + Date.now();
        appendChat('...', 'ai', loadingId);

        chrome.runtime.sendMessage(
            { type: "CHAT", url: currentUrl, message: text },
            (response) => {
                document.getElementById(loadingId)?.remove();
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
