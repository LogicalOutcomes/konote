/* KoNote Web — minimal vanilla JS for interactions */

// Tell HTMX to use the loading bar as a global indicator
document.body.setAttribute("hx-indicator", "#loading-bar");

// HTMX configuration
document.body.addEventListener("htmx:configRequest", function (event) {
    // Include CSRF token in HTMX requests
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
        event.detail.headers["X-CSRFToken"] = csrfToken.value;
    }
});

// --- Toast helper ---
function showToast(message, isError) {
    var toast = document.getElementById("htmx-error-toast");
    if (toast) {
        var msgEl = document.getElementById("htmx-error-toast-message");
        if (msgEl) {
            msgEl.textContent = message;
        } else {
            toast.textContent = message;
        }
        toast.hidden = false;
        // Only auto-dismiss non-error messages
        if (!isError) {
            setTimeout(function () { toast.hidden = true; }, 3000);
        }
    } else {
        alert(message);
    }
}

// Close button on toast
document.addEventListener("click", function (event) {
    if (event.target && event.target.id === "htmx-error-toast-close") {
        var toast = document.getElementById("htmx-error-toast");
        if (toast) { toast.hidden = true; }
    }
});

// Global HTMX error handler — show user-friendly message on network/server errors
document.body.addEventListener("htmx:responseError", function (event) {
    var status = event.detail.xhr ? event.detail.xhr.status : 0;
    var message = "Something went wrong. Please try again.";
    if (status === 403) {
        message = "You don't have permission to do that.";
    } else if (status === 404) {
        message = "The requested item was not found.";
    } else if (status >= 500) {
        message = "A server error occurred. Please try again later.";
    } else if (status === 0) {
        message = "Could not connect to the server. Check your internet connection.";
    }
    showToast(message, true);
});

// Handle HTMX send errors (network failures before response)
document.body.addEventListener("htmx:sendError", function () {
    showToast("Could not connect to the server. Check your internet connection.", true);
});

// --- Select All / Deselect All for metric checkboxes (export form) ---
document.addEventListener("click", function (event) {
    var target = event.target;
    if (target.id === "select-all-metrics" || target.id === "deselect-all-metrics") {
        event.preventDefault();
        var checked = target.id === "select-all-metrics";
        var fieldset = target.closest("fieldset");
        if (fieldset) {
            var checkboxes = fieldset.querySelectorAll("input[type='checkbox']");
            checkboxes.forEach(function (cb) { cb.checked = checked; });
        }
    }
});
