/* KoNote Web — minimal vanilla JS for interactions */

// Enable script execution in HTMX 2.0 swapped content (needed for Chart.js in Analysis tab)
// This must be set before any HTMX swaps occur
htmx.config.allowScriptTags = true;

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

// --- Auto-dismiss success messages after 3 seconds ---
// Error messages stay visible until manually dismissed
(function () {
    var AUTO_DISMISS_DELAY = 3000; // 3 seconds
    var FADE_DURATION = 300; // matches CSS animation

    // Check if user prefers reduced motion
    function prefersReducedMotion() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    // Dismiss a message with fade-out animation
    function dismissMessage(messageEl) {
        if (prefersReducedMotion()) {
            // Immediate removal for reduced motion preference
            messageEl.remove();
        } else {
            // Add fading class, then remove after animation completes
            messageEl.classList.add("fading-out");
            setTimeout(function () {
                messageEl.remove();
            }, FADE_DURATION);
        }
    }

    // Add close button to a message element
    function addCloseButton(messageEl) {
        var closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "message-close";
        closeBtn.setAttribute("aria-label", "Dismiss message");
        closeBtn.innerHTML = "&times;";
        closeBtn.addEventListener("click", function () {
            dismissMessage(messageEl);
        });
        messageEl.style.position = "relative";
        messageEl.appendChild(closeBtn);
    }

    // Set up auto-dismiss for success messages
    function setupAutoDismiss() {
        var messages = document.querySelectorAll("article[aria-label='notification']");
        messages.forEach(function (msg) {
            // Add close button to all messages
            addCloseButton(msg);

            // Check if this is a success message (auto-dismiss)
            // Django message tags: debug, info, success, warning, error
            var isSuccess = msg.classList.contains("success");
            var isError = msg.classList.contains("error") || msg.classList.contains("danger") || msg.classList.contains("warning");

            if (isSuccess && !isError) {
                // Auto-dismiss success messages after delay
                setTimeout(function () {
                    // Only dismiss if still in DOM (user might have manually closed it)
                    if (msg.parentNode) {
                        dismissMessage(msg);
                    }
                }, AUTO_DISMISS_DELAY);
            }
            // Error/warning messages stay until manually dismissed
        });
    }

    // Run on page load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupAutoDismiss);
    } else {
        setupAutoDismiss();
    }

    // Also run after HTMX swaps (in case messages are loaded dynamically)
    document.body.addEventListener("htmx:afterSwap", function (event) {
        // Only process if the swapped content might contain messages
        var newMessages = event.detail.target.querySelectorAll("article[aria-label='notification']");
        if (newMessages.length > 0) {
            setupAutoDismiss();
        }
    });
})();

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
