// Модальное подтверждение опасных действий: формы js-confirm открывают
// диалог structure/confirm_modal.html; без JS форма отправляется напрямую
(function () {
    const modal = document.getElementById("confirm-modal");
    const text = document.getElementById("confirm-modal-text");
    const submitButton = document.getElementById("confirm-modal-submit");
    const cancelButton = document.getElementById("confirm-modal-cancel");

    if (!modal || !text || !submitButton || !cancelButton) {
        return;
    }

    let pendingForm = null;

    function openModal(form) {
        pendingForm = form;
        text.textContent = form.dataset.confirm || "Вы уверены?";
        submitButton.textContent = form.dataset.confirmBtn || "Подтвердить";
        submitButton.className = "btn " + (form.dataset.confirmClass || "btn-danger");
        modal.classList.add("is-open");
        cancelButton.focus();
    }

    function closeModal() {
        modal.classList.remove("is-open");
        pendingForm = null;
    }

    // Перехват сабмита опасных форм: сначала диалог
    document.addEventListener("submit", function (event) {
        const form = event.target;
        if (!form.classList.contains("js-confirm")) {
            return;
        }
        event.preventDefault();
        openModal(form);
    });

    // Подтверждение отправляет отложенную форму
    submitButton.addEventListener("click", function () {
        if (pendingForm) {
            pendingForm.submit();
        }
        closeModal();
    });

    cancelButton.addEventListener("click", closeModal);

    // Клик по затемнению закрывает, по карточке — нет
    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    // ESC закрывает диалог
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("is-open")) {
            closeModal();
        }
    });
})();
