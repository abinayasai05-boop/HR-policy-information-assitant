
/* ============================================================
   HR POLICY AI ASSISTANT
   File: static/script.js

   Backend:
       POST /chat        -> { "answer": "..." }
       POST /clear-chat  -> optional chat memory reset

   Features:
       Text chat, voice input ON/OFF, voice output ON/OFF,
       Markdown formatting, typing indicator, auto-resize,
       clear chat, and error handling.
   ============================================================ */

"use strict";

/* ============================================================
   DOM ELEMENTS
   ============================================================ */

const messages = document.getElementById("messages");
const questionInput = document.getElementById("question");
const sendButton = document.getElementById("sendButton");

let voiceButton = document.getElementById("voiceButton");


const voiceInputToggle = document.getElementById("voiceInputToggle");
const voiceOutputToggle = document.getElementById("voiceOutputToggle");

/* ============================================================
   APPLICATION STATE
   ============================================================ */

let isSending = false;
let recognition = null;
let isListening = false;
let finalTranscript = "";

// Both voice features are OFF by default.
let voiceInputEnabled = false;
let voiceOutputEnabled = false;

/* ============================================================
   ENSURE MICROPHONE BUTTON EXISTS
   ============================================================ */

function ensureVoiceButtonExists() {
    const existingButton = document.getElementById("voiceButton");

    if (existingButton) {
        voiceButton = existingButton;
        return;
    }

    const inputBox = document.querySelector(
        "footer.input-area .input-box"
    );

    const sendBtn = document.getElementById("sendButton");

    if (!inputBox || !sendBtn) {
        console.error(
            "Microphone button could not be added: composer or send button is missing."
        );
        return;
    }

    voiceButton = document.createElement("button");
    voiceButton.id = "voiceButton";
    voiceButton.type = "button";
    voiceButton.className = "voice-button";
    voiceButton.textContent = "🎙️";
    voiceButton.title = "Enable Voice Input first";
    voiceButton.setAttribute(
        "aria-label",
        "Ask using your voice"
    );

    inputBox.insertBefore(voiceButton, sendBtn);
}

/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    ensureVoiceButtonExists();

    setupVoiceToggles();
    updateSendButton();
    initializeVoiceInput();

    if (questionInput) {
        questionInput.focus();
        autoResizeTextarea();
    }
});

/* Question input events */

if (questionInput) {
    questionInput.addEventListener("input", function () {
        updateSendButton();
        autoResizeTextarea();
    });
}

/* ============================================================
   VOICE INPUT AND OUTPUT TOGGLES
   ============================================================ */

function setupVoiceToggles() {
    // Voice Input toggle
    if (voiceInputToggle) {
        updateVoiceInputToggle();

        voiceInputToggle.addEventListener("click", function () {
            voiceInputEnabled = !voiceInputEnabled;

            updateVoiceInputToggle();

            // Stop listening immediately if voice input is switched off.
            if (
                !voiceInputEnabled &&
                recognition &&
                isListening
            ) {
                try {
                    recognition.stop();
                } catch (error) {
                    console.warn(
                        "Could not stop voice recognition:",
                        error
                    );
                }
            }
        });
    } else {
        console.warn(
            "Voice Input toggle not found. Add id='voiceInputToggle' in index.html."
        );
    }

    // Voice Output toggle
    if (voiceOutputToggle) {
        updateVoiceOutputToggle();

        voiceOutputToggle.addEventListener("click", function () {
            voiceOutputEnabled = !voiceOutputEnabled;

            updateVoiceOutputToggle();

            // Stop speaking immediately if voice output is switched off.
            if (
                !voiceOutputEnabled &&
                "speechSynthesis" in window
            ) {
                window.speechSynthesis.cancel();
            }
        });
    } else {
        console.warn(
            "Voice Output toggle not found. Add id='voiceOutputToggle' in index.html."
        );
    }
}

function updateVoiceInputToggle() {
    if (!voiceInputToggle) return;

    voiceInputToggle.textContent =
        `🎙️ Voice Input: ${voiceInputEnabled ? "ON" : "OFF"}`;

    voiceInputToggle.classList.toggle(
        "active",
        voiceInputEnabled
    );

    voiceInputToggle.setAttribute(
        "aria-pressed",
        String(voiceInputEnabled)
    );

    voiceInputToggle.title = voiceInputEnabled
        ? "Turn voice input off"
        : "Turn voice input on";

    if (voiceButton) {
        voiceButton.disabled = !voiceInputEnabled;

        voiceButton.title = voiceInputEnabled
            ? "Ask using your voice"
            : "Enable Voice Input first";

        voiceButton.setAttribute(
            "aria-label",
            voiceInputEnabled
                ? "Ask using your voice"
                : "Voice input is off"
        );
    }
}

function updateVoiceOutputToggle() {
    if (!voiceOutputToggle) return;

    voiceOutputToggle.textContent =
        `🔊 Voice Output: ${voiceOutputEnabled ? "ON" : "OFF"}`;

    voiceOutputToggle.classList.toggle(
        "active",
        voiceOutputEnabled
    );

    voiceOutputToggle.setAttribute(
        "aria-pressed",
        String(voiceOutputEnabled)
    );

    voiceOutputToggle.title = voiceOutputEnabled
        ? "Turn voice output off"
        : "Turn voice output on";

    // Cancel any currently spoken response when output is OFF.
    if (
        !voiceOutputEnabled &&
        "speechSynthesis" in window
    ) {
        window.speechSynthesis.cancel();
    }
}

/* ============================================================
   SEND BUTTON STATE
   ============================================================ */

function updateSendButton() {
    if (!sendButton || !questionInput) return;

    sendButton.disabled =
        isSending ||
        questionInput.value.trim().length === 0;
}

/* ============================================================
   KEYBOARD HANDLER
   Enter       = Send
   Shift+Enter = New line
   ============================================================ */

function handleKey(event) {
    if (!event || event.key !== "Enter" || event.shiftKey) {
        return;
    }

    event.preventDefault();

    if (!isSending) {
        sendMessage();
    }
}

/* ============================================================
   AUTO-RESIZE TEXTAREA
   ============================================================ */

function autoResizeTextarea() {
    if (!questionInput) return;

    questionInput.style.height = "auto";

    const maxHeight = 130;

    questionInput.style.height =
        Math.min(questionInput.scrollHeight, maxHeight) + "px";
}

/* ============================================================
   SUGGESTED QUESTIONS
   ============================================================ */

function askQuestion(question) {
    if (!questionInput || typeof question !== "string") return;
    if (!question.trim() || isSending) return;

    questionInput.value = question.trim();

    updateSendButton();
    autoResizeTextarea();

    sendMessage();
}

/* ============================================================
   SEND MESSAGE TO FLASK BACKEND
   ============================================================ */

async function sendMessage() {
    if (!questionInput || isSending) return;

    const question = questionInput.value.trim();

    if (!question) {
        updateSendButton();
        return;
    }

    isSending = true;
    updateSendButton();

    questionInput.disabled = true;

    // Stop microphone recognition while sending a question.
    if (recognition && isListening) {
        try {
            recognition.stop();
        } catch (error) {
            console.warn(
                "Could not stop voice recognition:",
                error
            );
        }
    }

    removeWelcomeContent();
    addUserMessage(question);

    questionInput.value = "";
    questionInput.style.height = "40px";

    showTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        let data;

        try {
            data = await response.json();
        } catch (error) {
            throw new Error(
                "The server returned an invalid response. " +
                "Check your Flask backend."
            );
        }

        if (!response.ok) {
            throw new Error(
                data && data.error
                    ? data.error
                    : "Server error: HTTP " + response.status
            );
        }

        if (
            !data ||
            typeof data.answer !== "string" ||
            !data.answer.trim()
        ) {
            throw new Error(
                "The server response must contain a non-empty answer."
            );
        }

        hideTypingIndicator();
        addAssistantMessage(data.answer);

    } catch (error) {
        console.error("Chat request failed:", error);

        hideTypingIndicator();

        addAssistantMessage(
            "Sorry, I couldn't retrieve an answer right now.\n\n" +
            "Please check that your Flask server is running and " +
            "that the /chat endpoint is working correctly.\n\n" +
            "Details: " + error.message
        );

    } finally {
        isSending = false;

        if (questionInput) {
            questionInput.disabled = false;
            updateSendButton();
            questionInput.focus();
        }
    }
}

/* ============================================================
   REMOVE WELCOME CONTENT
   ============================================================ */

function removeWelcomeContent() {
    if (!messages) return;

    const welcomeSection =
        messages.querySelector(".welcome-section");

    const welcomeCards =
        messages.querySelector(".welcome-cards");

    if (welcomeSection) welcomeSection.remove();
    if (welcomeCards) welcomeCards.remove();

    messages.style.justifyContent = "flex-start";
}

/* ============================================================
   ADD USER MESSAGE
   ============================================================ */

function addUserMessage(text) {
    if (!messages) return;

    const message = document.createElement("div");
    message.className = "chat-message user-message";

    const inner = document.createElement("div");
    inner.className = "chat-message-inner user-message-inner";

    const body = document.createElement("div");
    body.className = "message-body";

    const role = document.createElement("div");
    role.className = "message-role";
    role.textContent = "You";

    const messageText = document.createElement("div");
    messageText.className = "message-text user-text";
    messageText.textContent = text;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar user-avatar";
    avatar.textContent = "You";

    body.appendChild(role);
    body.appendChild(messageText);

    inner.appendChild(body);
    inner.appendChild(avatar);

    message.appendChild(inner);

    applyUserMessageStyles(message);

    messages.appendChild(message);
    scrollToBottom();
}

/* ============================================================
   ADD ASSISTANT MESSAGE
   ============================================================ */

function addAssistantMessage(text) {
    if (!messages) return;

    const message = document.createElement("div");
    message.className = "chat-message assistant-message";

    const inner = document.createElement("div");
    inner.className =
        "chat-message-inner assistant-message-inner";

    const avatar = document.createElement("div");
    avatar.className =
        "message-avatar assistant-message-avatar";
    avatar.textContent = "✦";

    const body = document.createElement("div");
    body.className = "message-body";

    const role = document.createElement("div");
    role.className = "message-role";
    role.textContent = "HR Policy Assistant";

    const messageText = document.createElement("div");
    messageText.className = "message-text assistant-text";

    // Escape source text before applying supported formatting.
    messageText.innerHTML = formatAssistantResponse(text);
    
const speakerButton = document.createElement("button");
speakerButton.type = "button";
speakerButton.className = "answer-speaker-button";
speakerButton.textContent = "🔊 Listen";
speakerButton.title = "Listen to this answer";
speakerButton.setAttribute("aria-label", "Listen to this answer");

speakerButton.addEventListener("click", function () {
    if (!("speechSynthesis" in window)) {
        alert("Speech playback is not supported in this browser.");
        return;
    }

    window.speechSynthesis.cancel();

    const cleanText = String(text)
        .replace(/```[\s\S]*?```/g, "Code omitted.")
        .replace(/[*_#`]/g, "")
        .replace(/^\s*[-•]\s+/gm, "")
        .replace(/\s+/g, " ")
        .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.pitch = 1;

    window.speechSynthesis.speak(utterance);
});

speakerButton.style.display = "block";
speakerButton.style.marginTop = "10px";
speakerButton.style.padding = "6px 12px";
speakerButton.style.borderRadius = "8px";
speakerButton.style.cursor = "pointer";

messageText.appendChild(speakerButton);

    body.appendChild(role);
    body.appendChild(messageText);

    inner.appendChild(avatar);
    inner.appendChild(body);

    message.appendChild(inner);

    applyAssistantMessageStyles(message);

    messages.appendChild(message);
    scrollToBottom();
}

/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHTML(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

/* ============================================================
   FORMAT ASSISTANT RESPONSE
   Supports bold, inline code, numbered lists and bullet lists.
   ============================================================ */

function formatAssistantResponse(text) {
    if (!text) return "";

    let formatted = escapeHTML(text);

    // Inline code.
    formatted = formatted.replace(
        /`([^`]+)`/g,
        "<code>$1</code>"
    );

    // Bold text.
    formatted = formatted.replace(
        /\*\*(.*?)\*\*/g,
        "<strong>$1</strong>"
    );

    // Numbered list items.
    formatted = formatted.replace(
        /^(\d+)\.\s+(.+)$/gm,
        '<div class="response-list-item"><strong>$1.</strong> $2</div>'
    );

    // Bullet list items.
    formatted = formatted.replace(
        /^[-*•]\s+(.+)$/gm,
        '<div class="response-list-item">• $1</div>'
    );

    // Preserve line breaks.
    formatted = formatted.replace(/\n/g, "<br>");

    return formatted;
}

/* ============================================================
   TYPING INDICATOR
   ============================================================ */

function showTypingIndicator() {
    if (!messages) return;

    hideTypingIndicator();

    const typing = document.createElement("div");
    typing.id = "typing";
    typing.className =
        "chat-message assistant-message typing-message";

    typing.innerHTML = `
        <div class="chat-message-inner assistant-message-inner">
            <div class="message-avatar assistant-message-avatar">✦</div>
            <div class="message-body">
                <div class="message-role">HR Policy Assistant</div>
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;

    applyAssistantMessageStyles(typing);

    messages.appendChild(typing);
    scrollToBottom();
}

function hideTypingIndicator() {
    const typing = document.getElementById("typing");

    if (typing) {
        typing.remove();
    }
}

/* ============================================================
   SCROLL TO BOTTOM
   ============================================================ */

function scrollToBottom() {
    if (!messages) return;

    messages.scrollTop = messages.scrollHeight;
}

/* ============================================================
   USER MESSAGE STYLING
   ============================================================ */

function applyUserMessageStyles(message) {
    if (!message) return;

    message.style.width = "100%";
    message.style.maxWidth = "850px";
    message.style.margin = "0 auto 18px";

    const inner = message.querySelector(".chat-message-inner");

    if (inner) {
        inner.style.display = "flex";
        inner.style.justifyContent = "flex-end";
        inner.style.alignItems = "flex-start";
        inner.style.gap = "10px";
    }

    const avatar = message.querySelector(".user-avatar");

    if (avatar) {
        avatar.style.width = "32px";
        avatar.style.height = "32px";
        avatar.style.minWidth = "32px";
        avatar.style.borderRadius = "10px";
        avatar.style.display = "grid";
        avatar.style.placeItems = "center";
        avatar.style.background = "rgba(139,92,246,.18)";
        avatar.style.color = "#c4b5fd";
        avatar.style.fontSize = "9px";
        avatar.style.fontWeight = "700";
    }

    const body = message.querySelector(".message-body");

    if (body) {
        body.style.maxWidth = "75%";
        body.style.order = "1";
        body.style.minWidth = "0";
    }

    const role = message.querySelector(".message-role");

    if (role) {
        role.style.textAlign = "right";
        role.style.color = "#7d7d8c";
        role.style.fontSize = "10px";
        role.style.marginBottom = "5px";
    }

    const text = message.querySelector(".message-text");

    if (text) {
        text.style.padding = "11px 14px";
        text.style.borderRadius = "16px 16px 4px 16px";
        text.style.background =
            "linear-gradient(135deg, #7c3aed, #9333ea)";
        text.style.color = "#ffffff";
        text.style.fontSize = "13px";
        text.style.lineHeight = "1.6";
        text.style.wordBreak = "break-word";
        text.style.whiteSpace = "pre-wrap";
    }
}

/* ============================================================
   ASSISTANT MESSAGE STYLING
   ============================================================ */

function applyAssistantMessageStyles(message) {
    if (!message) return;

    message.style.width = "100%";
    message.style.maxWidth = "850px";
    message.style.margin = "0 auto 20px";

    const inner = message.querySelector(".chat-message-inner");

    if (inner) {
        inner.style.display = "flex";
        inner.style.alignItems = "flex-start";
        inner.style.gap = "10px";
    }

    const avatar =
        message.querySelector(".assistant-message-avatar");

    if (avatar) {
        avatar.style.width = "32px";
        avatar.style.height = "32px";
        avatar.style.minWidth = "32px";
        avatar.style.borderRadius = "10px";
        avatar.style.display = "grid";
        avatar.style.placeItems = "center";
        avatar.style.background =
            "linear-gradient(145deg,#7c3aed,#a855f7)";
        avatar.style.color = "#ffffff";
        avatar.style.fontSize = "14px";
    }

    const body = message.querySelector(".message-body");

    if (body) {
        body.style.flex = "1";
        body.style.minWidth = "0";
    }

    const role = message.querySelector(".message-role");

    if (role) {
        role.style.color = "#a78bfa";
        role.style.fontSize = "10px";
        role.style.fontWeight = "700";
        role.style.marginBottom = "5px";
    }

    const text = message.querySelector(".assistant-text");

    if (text) {
        text.style.color = "#d5d5df";
        text.style.fontSize = "13px";
        text.style.lineHeight = "1.75";
        text.style.wordBreak = "break-word";
        text.style.whiteSpace = "normal";
    }

    message.querySelectorAll("code").forEach(function (element) {
        element.style.padding = "2px 5px";
        element.style.borderRadius = "5px";
        element.style.background = "rgba(255,255,255,.07)";
        element.style.color = "#c4b5fd";
        element.style.fontFamily = "Consolas, monospace";
    });

    message.querySelectorAll("strong").forEach(function (element) {
        element.style.color = "#f1efff";
    });

    message.querySelectorAll(".response-list-item").forEach(
        function (element) {
            element.style.marginTop = "5px";
            element.style.paddingLeft = "4px";
        }
    );

    message.querySelectorAll(".typing-indicator span").forEach(
        function (dot) {
            dot.style.display = "inline-block";
            dot.style.width = "6px";
            dot.style.height = "6px";
            dot.style.marginRight = "4px";
            dot.style.borderRadius = "50%";
            dot.style.background = "#a78bfa";
            dot.style.animation =
                "typingPulse 1.2s infinite ease-in-out";
        }
    );
}


/* ============================================================
   VOICE INPUT AND OUTPUT
   Uses the existing variables and toggle functions above.
   ============================================================ */
   
function initializeVoiceInput() {
    if (!voiceButton || !questionInput) {
        console.warn("Voice button or question input not found.");
        return;
    }

    const SpeechRecognitionAPI =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
        voiceButton.disabled = true;
        voiceButton.title =
            "Voice input is not supported. Try Chrome or Edge.";
        console.warn("Speech recognition is not supported.");
        return;
    }

    recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = function () {
        isListening = true;
        finalTranscript = "";

        voiceButton.textContent = "🔴";
        voiceButton.classList.add("listening");
        voiceButton.title = "Listening... Click again to finish";
    };
    

recognition.onresult = function (event) {
    if (!voiceInputEnabled || !questionInput) return;

    const finalParts = [];
    let interimText = "";

    for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript.trim();

        if (!text) continue;

        if (result.isFinal) {
            finalParts.push(text);
        } else {
            // Keep only the current interim result.
            interimText = text;
        }
    }

    finalTranscript = finalParts.join(" ").trim();

    // Show finalized words plus the current unfinished words.
    questionInput.value = [
        finalTranscript,
        interimText
    ].filter(Boolean).join(" ").trim();

    updateSendButton();
    autoResizeTextarea();
};

recognition.onerror = function (event) {
    console.error("Voice recognition error:", event.error);

    const errors = {
        "not-allowed":
            "Microphone access denied. Allow microphone access in Chrome settings.",
        "service-not-allowed":
            "The browser has blocked speech recognition.",
        "no-speech":
            "No speech detected. Please try again.",
        "audio-capture":
            "No microphone detected. Check your microphone connection.",
        "network":
            "Speech recognition network error. Check your internet connection."
    };

    if (event.error !== "aborted") {
        alert(
            errors[event.error] ||
            "Microphone error: " + event.error
        );
    }
};

recognition.onend = function () {
    isListening = false;

    if (voiceButton) {
        voiceButton.classList.remove("listening");
        voiceButton.textContent = "🎙️";
        voiceButton.disabled = !voiceInputEnabled;
        voiceButton.title = voiceInputEnabled
            ? "Ask using your voice"
            : "Enable Voice Input first";
    }

    const question = finalTranscript.trim();
    finalTranscript = "";

    if (!voiceInputEnabled || !question || isSending) {
        return;
    }

    questionInput.value = question;
    updateSendButton();
    autoResizeTextarea();

    sendMessage();
};

voiceButton.addEventListener("click", function () {
    if (!voiceInputEnabled) {
        alert("Please switch Voice Input ON first.");
        return;
    }

    if (isSending) return;

    if (isListening) {
        voiceButton.disabled = true;
        voiceButton.textContent = "⏳";
        voiceButton.title = "Finishing voice input...";

        try {
            recognition.stop();
        } catch (error) {
            console.error("Could not stop microphone:", error);
            voiceButton.disabled = false;
        }

        return;
    }

    finalTranscript = "";

    try {
        recognition.start();
    } catch (error) {
        console.error("Could not start microphone:", error);
    }
});
}

/* ============================================================
   SPEAK ASSISTANT RESPONSES
   ============================================================ */

function speakAssistantResponse(text) {
    if (
        !voiceOutputEnabled ||
        !("speechSynthesis" in window) ||
        !text
    ) {
        return;
    }

    window.speechSynthesis.cancel();

    const cleanText = String(text)
        .replace(/```[\s\S]*?```/g, "Code omitted.")
        .replace(/<[^>]*>/g, " ")
        .replace(/\*\*/g, "")
        .replace(/[`*_#]/g, "")
        .replace(/^\s*[-•]\s+/gm, "")
        .replace(/\s+/g, " ")
        .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.pitch = 1;

    window.speechSynthesis.speak(utterance);
}
/* ============================================================
   CLEAR CHAT / NEW CONVERSATION
   ============================================================ */

async function clearChat() {
    if (isSending) return;

    // Stop speech output.
    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }

    // Stop voice input if active.
    if (recognition && isListening) {
        try {
            recognition.stop();
        } catch (error) {
            console.warn(
                "Could not stop recognition:",
                error
            );
        }
    }

    if (messages) {
        messages.innerHTML = `
            <div class="welcome-section">
                <div class="welcome-logo">✦</div>
                <div class="welcome-badge">
                    <span class="badge-dot"></span>
                    AI-POWERED HR KNOWLEDGE BASE
                </div>
                <h2>How can I help you?</h2>
                <p>
                    Ask questions about company policies,
                    employee benefits, leave, attendance,
                    remote work, compensation and more.
                </p>
            </div>

            <div class="welcome-cards">
                <div class="welcome-card"
                     onclick="askQuestion('How many days of annual leave can employees take?')">
                    <div class="card-icon">🏖️</div>
                    <div class="card-content">
                        <strong>Annual Leave</strong>
                        <small>Entitlement, eligibility and leave rules</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>

                <div class="welcome-card"
                     onclick="askQuestion('What is the maternity leave policy?')">
                    <div class="card-icon">👶</div>
                    <div class="card-content">
                        <strong>Maternity Leave</strong>
                        <small>Benefits, duration and eligibility</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>

                <div class="welcome-card"
                     onclick="askQuestion('Can employees work from home?')">
                    <div class="card-icon">🏠</div>
                    <div class="card-content">
                        <strong>Remote Work</strong>
                        <small>Work-from-home requirements</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>

                <div class="welcome-card"
                     onclick="askQuestion('What are the standard working hours?')">
                    <div class="card-icon">🕘</div>
                    <div class="card-content">
                        <strong>Working Hours</strong>
                        <small>Attendance and standard schedules</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>

                <div class="welcome-card"
                     onclick="askQuestion('What is the notice period when resigning?')">
                    <div class="card-icon">📄</div>
                    <div class="card-content">
                        <strong>Resignation</strong>
                        <small>Notice periods and exit policies</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>

                <div class="welcome-card"
                     onclick="askQuestion('How is salary paid to employees?')">
                    <div class="card-icon">💰</div>
                    <div class="card-content">
                        <strong>Compensation</strong>
                        <small>Salary and compensation policies</small>
                    </div>
                    <span class="card-arrow">→</span>
                </div>
            </div>
        `;

        messages.style.justifyContent = "center";
    }

    hideTypingIndicator();

    if (questionInput) {
        questionInput.value = "";
        questionInput.style.height = "40px";
        questionInput.disabled = false;
        questionInput.focus();
    }

    updateSendButton();

    // The UI reset works even if /clear-chat is not implemented.
    try {
        const response = await fetch("/clear-chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            console.warn(
                "The backend chat memory was not cleared. " +
                "Check whether /clear-chat exists."
            );
        }
    } catch (error) {
        console.warn(
            "Could not reset backend chat memory. The UI was reset.",
            error
        );
    }
}

function newConversation() {
    clearChat();
}

/* ============================================================
   KEYBOARD SHORTCUT
   Ctrl+K / Cmd+K focuses the question input.
   ============================================================ */

document.addEventListener("keydown", function (event) {
    if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k"
    ) {
        event.preventDefault();

        if (questionInput) {
            questionInput.focus();
        }
    }
});

/* ============================================================
   GLOBAL FUNCTIONS
   Used by inline HTML event handlers.
   ============================================================ */

window.sendMessage = sendMessage;
window.askQuestion = askQuestion;
window.handleKey = handleKey;
window.clearChat = clearChat;
window.newConversation = newConversation;

/* ============================================================
   ANIMATION STYLES
   ============================================================ */

const typingStyle = document.createElement("style");

typingStyle.textContent = `
    @keyframes typingPulse {
        0%, 60%, 100% {
            opacity: .35;
            transform: translateY(0);
        }
        30% {
            opacity: 1;
            transform: translateY(-3px);
        }
    }

    #sendButton:disabled {
        opacity: .45;
        cursor: not-allowed;
        transform: none !important;
    }

    .chat-message {
        animation: messageAppear .22s ease-out both;
    }

    @keyframes messageAppear {
        from {
            opacity: 0;
            transform: translateY(5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .voice-toggle.active {
        border-color: #8b5cf6;
        background: rgba(139, 92, 246, .2);
        color: #c4b5fd;
    }

    .voice-toggle {
        cursor: pointer;
        transition: background .2s ease, color .2s ease;
    }
`;

document.head.appendChild(typingStyle);

/* ============================================================
   INITIAL STATE
   ============================================================ */

updateSendButton();
hideTypingIndicator(); 