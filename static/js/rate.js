"use strict";

const institutionSelect = document.getElementById("institution_id");
const cabinetSelect = document.getElementById("cabinet_id");
const cabinetHint = document.getElementById("cabinet-hint");
const cabinets = JSON.parse(
    document.getElementById("cabinets-data").textContent
);

function updateCabinets(selectedCabinetId = "") {
    const institutionId = institutionSelect.value;

    cabinetSelect.replaceChildren();
    cabinetSelect.disabled = true;

    if (!institutionId) {
        cabinetSelect.add(new Option("Сначала выберите учреждение", ""));
        cabinetHint.textContent = "После выбора учреждения здесь появятся его кабинеты.";
        return;
    }

    const matchingCabinets = cabinets.filter(
        (cabinet) => String(cabinet.institution_id) === institutionId
    );

    cabinetSelect.add(new Option("Без указания кабинета", ""));

    if (matchingCabinets.length === 0) {
        cabinetHint.textContent = "Кабинеты пока не добавлены. Отметка будет сохранена для учреждения.";
        return;
    }

    for (const cabinet of matchingCabinets) {
        const label = cabinet.cabinet_type
            ? `${cabinet.name} — ${cabinet.cabinet_type}`
            : cabinet.name;

        const option = new Option(label, String(cabinet.id));
        option.selected = String(cabinet.id) === selectedCabinetId;
        cabinetSelect.add(option);
    }

    cabinetSelect.disabled = false;
    cabinetHint.textContent = "Выберите кабинет или оставьте отметку без его указания.";
}

institutionSelect.addEventListener("change", () => {
    updateCabinets();
});

updateCabinets(cabinetSelect.dataset.selectedCabinet);