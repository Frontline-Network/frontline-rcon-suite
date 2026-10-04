(() => {
    const fillEmptyApiKey = (input) => {
        if (input && !input.value && typeof window.crypto?.randomUUID === "function") {
            input.value = window.crypto.randomUUID();
        }
    };
    document.addEventListener("formset:added", (event) => {
        if (event.detail.formsetName === "djangoapikey_set") {
            fillEmptyApiKey(document.getElementById(`id_${event.target.id}-api_key`));
        }
    });
    const initialize = () => fillEmptyApiKey(document.getElementById("id_api_key"));
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
        initialize();
    }
})();
