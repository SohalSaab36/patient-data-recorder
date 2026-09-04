document.addEventListener("DOMContentLoaded", function () {
    const panes = Array.from(document.querySelectorAll(".wizard-pane"));
    const steps = Array.from(document.querySelectorAll("#wizardSteps li"));
    const prevBtn = document.getElementById("prevStep");
    const nextBtn = document.getElementById("nextStep");
    const submitBtn = document.getElementById("submitCase");
    const form = document.getElementById("caseForm");
    if (!form || !panes.length) return;

    let current = 1;
    const total = panes.length;

    function show(step) {
        current = step;
        panes.forEach(function (pane) {
            pane.classList.toggle("active", Number(pane.dataset.pane) === step);
        });
        steps.forEach(function (item) {
            const n = Number(item.dataset.step);
            item.classList.toggle("active", n === step);
            item.classList.toggle("done", n < step);
        });
        prevBtn.disabled = step === 1;
        nextBtn.classList.toggle("d-none", step === total);
        submitBtn.classList.toggle("d-none", step !== total);
    }

    function fieldsInPane(pane) {
        return Array.from(pane.querySelectorAll("input, select, textarea"));
    }

    function validateCurrent() {
        const pane = panes.find(function (p) {
            return Number(p.dataset.pane) === current;
        });
        let ok = true;
        fieldsInPane(pane).forEach(function (field) {
            if (!field.checkValidity()) {
                field.reportValidity();
                ok = false;
            }
        });
        return ok;
    }

    nextBtn.addEventListener("click", function () {
        if (!validateCurrent()) return;
        if (current < total) show(current + 1);
    });

    prevBtn.addEventListener("click", function () {
        if (current > 1) show(current - 1);
    });

    form.addEventListener("submit", function (event) {
        for (let i = 1; i <= total; i += 1) {
            current = i;
            if (!validateCurrent()) {
                event.preventDefault();
                show(i);
                return;
            }
        }
    });

    show(1);
});
