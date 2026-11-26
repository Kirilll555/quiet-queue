"use strict";

(() => {
    const toggle = document.getElementById("nav-toggle");
    const menu = document.getElementById("nav-menu");
    const mobileScreen = window.matchMedia("(max-width: 1000px)");

    function setExpanded(expanded) {
        menu.hidden = !expanded;
        toggle.setAttribute("aria-expanded", String(expanded));
    }

    function updateLayout() {
        const focusWasInMenu = menu.contains(document.activeElement);
        const focusWasOnToggle = document.activeElement === toggle;

        toggle.hidden = !mobileScreen.matches;
        setExpanded(!mobileScreen.matches);

        if (mobileScreen.matches && focusWasInMenu) {
            toggle.focus();
        } else if (!mobileScreen.matches && focusWasOnToggle) {
            menu.querySelector("a").focus();
        }
    }

    toggle.addEventListener("click", () => {
        setExpanded(menu.hidden);
    });

    document.addEventListener("keydown", (event) => {
        if (
            event.key === "Escape"
            && mobileScreen.matches
            && !menu.hidden
        ) {
            setExpanded(false);
            toggle.focus();
        }
    });

    mobileScreen.addEventListener("change", updateLayout);
    updateLayout();
})();