document.addEventListener("DOMContentLoaded", function () {
    const script = document.querySelector("script[data-lang]");
    const lang = script ? script.getAttribute("data-lang") : "en-IN";
    const micBtn = document.getElementById("micBtn");
    const answer = document.getElementById("answer");
    const status = document.getElementById("voiceStatus");
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    document.querySelectorAll(".tts-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const bubble = btn.closest(".bubble");
            const text = bubble ? bubble.innerText.replace("Hear question", "").trim() : "";
            if (!window.speechSynthesis || !text) return;
            const utter = new SpeechSynthesisUtterance(text);
            utter.lang = lang;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
        });
    });

    if (!micBtn || !answer) return;
    if (!SpeechRecognition) {
        micBtn.disabled = true;
        if (status) status.textContent = "Voice is not available in this browser. Type your answer instead.";
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    micBtn.addEventListener("click", function () {
        try {
            recognition.start();
            if (status) status.textContent = "Listening… speak, then edit the text if needed.";
        } catch (err) {
            if (status) status.textContent = "Could not start the microphone. Type your answer instead.";
        }
    });
    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        answer.value = transcript;
        if (status) status.textContent = "Transcript ready. Edit if needed, then send.";
        answer.focus();
    };
    recognition.onerror = function () {
        if (status) status.textContent = "Voice capture failed. You can still type.";
    };
});
