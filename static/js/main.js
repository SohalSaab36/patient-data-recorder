document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("menuToggle");
    const backdrop = document.getElementById("sidebarBackdrop");

    function closeMenu() {
        if (!sidebar) return;
        sidebar.classList.remove("open");
        if (backdrop) backdrop.classList.remove("show");
    }

    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
            if (backdrop) backdrop.classList.toggle("show");
        });
    }
    if (backdrop) backdrop.addEventListener("click", closeMenu);

    document.querySelectorAll("[data-tts]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const text = btn.getAttribute("data-tts") || "";
            if (!window.speechSynthesis || !text) return;
            const utter = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
        });
    });
});
