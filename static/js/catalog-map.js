"use strict";

(() => {
    const listButton = document.getElementById("show-list");
    const mapButton = document.getElementById("show-map");
    const listPanel = document.getElementById("institution-list");
    const mapPanel = document.getElementById("institution-map-panel");
    const mapMessage = document.getElementById("map-message");
    const mapElement = document.getElementById("institution-map");
    const institutions = JSON.parse(
        document.getElementById("map-institutions-data").textContent
    );

    let map = null;
    const desktopScreen = window.matchMedia("(min-width: 1001px)");

    function escapeHtml(value) {
        const element = document.createElement("div");
        element.textContent = String(value);
        return element.innerHTML;
    }

    function createMap() {
        map = new ymaps.Map("institution-map", {
            center: [42.98, 47.50],
            zoom: 12,
            controls: ["zoomControl"],
        });

        for (const institution of institutions) {
            const popup = document.createElement("div");

            const address = document.createElement("p");
            address.textContent = institution.address;

            const status = document.createElement("p");
            status.textContent = `Общая очередь: ${institution.queue_label}`;

            const link = document.createElement("a");
            link.href = institution.rate_url;
            link.textContent = "Сообщить о ситуации";

            popup.append(address, status, link);

            const marker = new ymaps.Placemark(
                [institution.latitude, institution.longitude],
                {
                    hintContent: escapeHtml(institution.name),
                    balloonContentHeader: escapeHtml(institution.name),
                    balloonContentBody: popup.innerHTML,
                },
                {
                    preset: "islands#darkGreenDotIcon",
                }
            );

            map.geoObjects.add(marker);
        }

        if (institutions.length === 1) {
            const institution = institutions[0];
            map.setCenter(
                [institution.latitude, institution.longitude],
                15
            );
        } else {
            map.setBounds(map.geoObjects.getBounds(), {
                checkZoomRange: true,
                zoomMargin: 30,
            });
        }
    }

    function showView(showMap) {
        listPanel.hidden = showMap && !desktopScreen.matches;
        mapPanel.hidden = !showMap;

        listButton.setAttribute("aria-pressed", String(!showMap));
        mapButton.setAttribute("aria-pressed", String(showMap));

        listButton.classList.toggle("btn-primary", !showMap);
        listButton.classList.toggle("btn-secondary", showMap);
        mapButton.classList.toggle("btn-primary", showMap);
        mapButton.classList.toggle("btn-secondary", !showMap);

        if (!showMap) {
            return;
        }

        if (institutions.length === 0) {
            mapElement.hidden = true;
            mapMessage.textContent = "Для найденных учреждений пока нет координат. Воспользуйтесь списком.";
            return;
        }

        mapMessage.textContent = `Учреждений на карте: ${institutions.length}.`;

        try {
            if (map === null) {
                createMap();
            }

            map.container.fitToViewport();
        } catch (error) {
            mapMessage.textContent = "Не удалось открыть карту. Воспользуйтесь списком.";
            console.error("Ошибка карты:", error);
        }
    }

    listButton.addEventListener("click", () => showView(false));
    mapButton.addEventListener("click", () => showView(true));

    if (typeof ymaps === "undefined") {
        mapButton.textContent = "Карта недоступна";
        mapButton.title = "Проверьте подключение к интернету и настройку API.";
        return;
    }

    ymaps.ready(
        () => {
            mapButton.disabled = false;
            desktopScreen.addEventListener("change", () => {
                showView(desktopScreen.matches);
            });
            showView(desktopScreen.matches);
        },
        () => {
            mapButton.textContent = "Карта недоступна";
        }
    );
})();