const readingModeToggle = document.getElementById("reading-mode-toggle");
const readingModeKey = "quiet-queue-reading-mode";

if (readingModeToggle) {
    let enabled = false;

    try {
        enabled = localStorage.getItem(readingModeKey) === "on";
    } catch {
        // Если хранилище недоступно, переключатель работает на открытой странице.
    }

    function applyReadingMode() {
        document.documentElement.dataset.readingMode = enabled ? "on" : "off";
        readingModeToggle.setAttribute("aria-pressed", String(enabled));
    }

    applyReadingMode();
    readingModeToggle.hidden = false;

    readingModeToggle.addEventListener("click", () => {
        enabled = !enabled;
        applyReadingMode();

        try {
            localStorage.setItem(readingModeKey, enabled ? "on" : "off");
        } catch {
            // Выбранный режим уже применён на этой странице.
        }
    });
}