/* KoNote Web — minimal vanilla JS for interactions */

// Translated strings helper — reads from window.KN (set in base.html)
// Falls back to English if KN not loaded
var KN = window.KN || {};
function t(key, fallback) {
    return KN[key] || fallback;
}

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

// --- Link form error messages to their inputs (aria-describedby) ---
// Scans for <small class="error" id="..."> and links the preceding input/select/textarea
(function () {
    function linkErrorMessages() {
        var errors = document.querySelectorAll("small.error[id]");
        errors.forEach(function (errorEl) {
            // Walk backwards through siblings to find the form control
            var sibling = errorEl.previousElementSibling;
            while (sibling) {
                var input = null;
                var tag = sibling.tagName.toLowerCase();
                if (tag === "input" || tag === "textarea" || tag === "select") {
                    input = sibling;
                } else {
                    // Check inside the sibling (Django might wrap inputs)
                    input = sibling.querySelector("input, textarea, select");
                }
                if (input) {
                    var existing = input.getAttribute("aria-describedby");
                    if (existing) {
                        input.setAttribute("aria-describedby", existing + " " + errorEl.id);
                    } else {
                        input.setAttribute("aria-describedby", errorEl.id);
                    }
                    input.setAttribute("aria-invalid", "true");
                    break;
                }
                sibling = sibling.previousElementSibling;
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", linkErrorMessages);
    } else {
        linkErrorMessages();
    }
})();

// --- Auto-dismiss success messages after 8 seconds ---
// Error messages stay visible until manually dismissed
(function () {
    var AUTO_DISMISS_DELAY = 8000; // 8 seconds (WCAG 2.2.1 — allow time to read)
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
        closeBtn.setAttribute("aria-label", t("dismissMessage", "Dismiss message"));
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
            setTimeout(function () { toast.hidden = true; }, 8000);
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
    var message = t("errorGeneric", "Something went wrong. Please try again.");
    if (status === 403) {
        message = t("error403", "You don't have permission to do that.");
    } else if (status === 404) {
        message = t("error404", "The requested item was not found.");
    } else if (status >= 500) {
        message = t("error500", "A server error occurred. Please try again later.");
    } else if (status === 0) {
        message = t("errorNetwork", "Could not connect to the server. Check your internet connection.");
    }
    showToast(message, true);
});

// Handle HTMX send errors (network failures before response)
document.body.addEventListener("htmx:sendError", function () {
    showToast(t("errorNetwork", "Could not connect to the server. Check your internet connection."), true);
});

// Focus management for note detail expansion (accessibility)
// When a note card expands via HTMX, move focus to the detail content
document.body.addEventListener("htmx:afterSwap", function (event) {
    var detail = event.detail.target.querySelector(".note-detail-content");
    if (detail) {
        detail.focus();
    }
});

// BLOCKER-2: Focus main content on page load (WCAG 2.4.3)
// After login redirect or page navigation, move focus to <main> so
// keyboard/screen reader users start from the content, not the footer.
(function () {
    function focusMainContent() {
        var main = document.getElementById("main-content");
        if (!main) return;
        // Don't override if URL targets a specific element
        if (window.location.hash) return;
        // Don't override if something other than body already has focus
        if (document.activeElement && document.activeElement !== document.body &&
            document.activeElement.tagName !== "HTML") return;
        main.focus({ preventScroll: true });
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", focusMainContent);
    } else {
        focusMainContent();
    }
})();

// Keyboard activation for role="button" elements (WCAG 2.1.1 — Enter/Space triggers click)
document.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") &&
        e.target.getAttribute("role") === "button" &&
        e.target.tagName !== "BUTTON" &&
        e.target.tagName !== "A") {
        e.preventDefault();
        e.target.click();
    }
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

// --- Mobile navigation toggle ---
(function () {
    function setupMobileNav() {
        var navToggle = document.getElementById("nav-toggle");
        var navMenu = document.getElementById("nav-menu");

        if (!navToggle || !navMenu) return;

        navToggle.addEventListener("click", function () {
            var isOpen = navMenu.classList.toggle("nav-open");
            navToggle.setAttribute("aria-expanded", isOpen);
        });

        // Close menu when clicking outside
        document.addEventListener("click", function (event) {
            var nav = document.querySelector("body > nav");
            if (nav && !nav.contains(event.target) && navMenu.classList.contains("nav-open")) {
                navMenu.classList.remove("nav-open");
                navToggle.setAttribute("aria-expanded", "false");
            }
        });

        // Close menu when window is resized above mobile breakpoint
        window.addEventListener("resize", function () {
            if (window.innerWidth > 768 && navMenu.classList.contains("nav-open")) {
                navMenu.classList.remove("nav-open");
                navToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupMobileNav);
    } else {
        setupMobileNav();
    }
})();

// --- Note Auto-Save / Draft Recovery ---
// Saves form data to localStorage as user types, restores on page load
(function () {
    var AUTOSAVE_DELAY = 1000; // Save 1 second after user stops typing
    var STORAGE_PREFIX = "KoNote_draft_";

    // Debounce helper
    function debounce(fn, delay) {
        var timer = null;
        return function () {
            var context = this;
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(context, args);
            }, delay);
        };
    }

    // Get storage key for a form
    function getStorageKey(form) {
        var clientId = form.getAttribute("data-client-id");
        var formType = form.getAttribute("data-form-type") || "note";
        if (!clientId) return null;
        return STORAGE_PREFIX + formType + "_" + clientId;
    }

    // Collect form data into an object
    function collectFormData(form) {
        var data = {};
        var inputs = form.querySelectorAll("input, textarea, select");
        inputs.forEach(function (el) {
            // Skip CSRF token, submit buttons, and consent checkbox
            if (el.name === "csrfmiddlewaretoken" || el.type === "submit") return;
            if (el.name === "consent_confirmed") return; // Don't save consent - must be re-confirmed

            if (el.type === "checkbox") {
                // For checkboxes, store checked state with unique key
                var key = el.name || el.getAttribute("data-target-id");
                if (el.classList.contains("target-selector")) {
                    key = "target_selector_" + el.getAttribute("data-target-id");
                }
                data[key] = el.checked;
            } else if (el.type === "radio") {
                if (el.checked) {
                    data[el.name] = el.value;
                }
            } else {
                data[el.name] = el.value;
            }
        });
        return data;
    }

    // Restore form data from saved object
    function restoreFormData(form, data) {
        var inputs = form.querySelectorAll("input, textarea, select");
        inputs.forEach(function (el) {
            if (el.name === "csrfmiddlewaretoken" || el.type === "submit") return;
            if (el.name === "consent_confirmed") return;

            if (el.type === "checkbox") {
                var key = el.name || el.getAttribute("data-target-id");
                if (el.classList.contains("target-selector")) {
                    key = "target_selector_" + el.getAttribute("data-target-id");
                }
                if (data.hasOwnProperty(key)) {
                    el.checked = data[key];
                    // Trigger change event for target selectors to show/hide details
                    if (el.classList.contains("target-selector")) {
                        el.dispatchEvent(new Event("change"));
                    }
                }
            } else if (el.type === "radio") {
                if (data[el.name] === el.value) {
                    el.checked = true;
                }
            } else if (data.hasOwnProperty(el.name)) {
                el.value = data[el.name];
            }
        });
    }

    // Check if form data has meaningful content worth saving
    function hasContent(data) {
        for (var key in data) {
            if (!data.hasOwnProperty(key)) continue;
            var val = data[key];
            // Check for non-empty text values (ignore dates/dropdowns set to defaults)
            if (typeof val === "string" && val.trim() !== "" && key !== "session_date" && key !== "template") {
                return true;
            }
            // Check for checked target selectors
            if (key.startsWith("target_selector_") && val === true) {
                return true;
            }
        }
        return false;
    }

    // Save draft to localStorage
    function saveDraft(form) {
        var key = getStorageKey(form);
        if (!key) return;

        var data = collectFormData(form);
        if (hasContent(data)) {
            data._savedAt = new Date().toISOString();
            try {
                localStorage.setItem(key, JSON.stringify(data));
            } catch (e) {
                // localStorage might be full or disabled - fail silently
                console.warn("Could not save draft:", e);
            }
        }
    }

    // Load draft from localStorage
    function loadDraft(form) {
        var key = getStorageKey(form);
        if (!key) return null;

        try {
            var stored = localStorage.getItem(key);
            if (stored) {
                return JSON.parse(stored);
            }
        } catch (e) {
            console.warn("Could not load draft:", e);
        }
        return null;
    }

    // Clear draft from localStorage
    function clearDraft(form) {
        var key = getStorageKey(form);
        if (!key) return;
        try {
            localStorage.removeItem(key);
        } catch (e) {
            // Ignore errors
        }
    }

    // Format saved time for display
    function formatSavedTime(isoString) {
        try {
            var date = new Date(isoString);
            var now = new Date();
            var diffMs = now - date;
            var diffMins = Math.floor(diffMs / 60000);

            if (diffMins < 1) return t("justNow", "just now");
            if (diffMins === 1) return t("oneMinuteAgo", "1 minute ago");
            if (diffMins < 60) return t("minutesAgo", "{n} minutes ago").replace("{n}", diffMins);

            var diffHours = Math.floor(diffMins / 60);
            if (diffHours === 1) return t("oneHourAgo", "1 hour ago");
            if (diffHours < 24) return t("hoursAgo", "{n} hours ago").replace("{n}", diffHours);

            // Show date for older drafts
            return date.toLocaleDateString();
        } catch (e) {
            return t("earlier", "earlier");
        }
    }

    // Create and show the draft recovery banner
    function showRecoveryBanner(form, draft) {
        var savedTime = draft._savedAt ? formatSavedTime(draft._savedAt) : t("earlier", "earlier");

        var banner = document.createElement("article");
        banner.className = "draft-recovery-banner";
        banner.setAttribute("role", "alert");
        banner.innerHTML =
            '<p><strong>' + t("draftFound", "Draft found") + '</strong> — ' +
            t("unsavedWork", "You have unsaved work from {time}.").replace("{time}", savedTime) + '</p>' +
            '<div role="group">' +
            '<button type="button" class="draft-restore">' + t("restoreDraft", "Restore draft") + '</button>' +
            '<button type="button" class="draft-discard outline secondary">' + t("discard", "Discard") + '</button>' +
            '</div>';

        // Insert banner before the form
        form.parentNode.insertBefore(banner, form);

        // Handle restore
        banner.querySelector(".draft-restore").addEventListener("click", function () {
            restoreFormData(form, draft);
            banner.remove();
            showToast(t("draftRestored", "Draft restored"), false);
        });

        // Handle discard
        banner.querySelector(".draft-discard").addEventListener("click", function () {
            clearDraft(form);
            banner.remove();
        });
    }

    // Show autosave indicator
    function showAutosaveIndicator(status) {
        var indicator = document.getElementById("autosave-status");
        if (!indicator) return;

        var statusText = indicator.querySelector(".status-text");
        indicator.hidden = false;
        indicator.classList.remove("saving", "saved");

        if (status === "saving") {
            indicator.classList.add("saving");
            if (statusText) statusText.textContent = t("saving", "Saving…");
        } else if (status === "saved") {
            indicator.classList.add("saved");
            if (statusText) statusText.textContent = t("saved", "Saved");
            // Hide after 2 seconds
            setTimeout(function() {
                indicator.hidden = true;
            }, 2000);
        }
    }

    // Initialize auto-save on a form (updated with visual feedback)
    function initAutoSave(form) {
        var key = getStorageKey(form);
        if (!key) return; // Form doesn't have required data attributes

        // Check for existing draft and show recovery banner
        var draft = loadDraft(form);
        if (draft && hasContent(draft)) {
            showRecoveryBanner(form, draft);
        }

        // Set up auto-save on input with visual feedback
        var debouncedSave = debounce(function () {
            showAutosaveIndicator("saving");
            saveDraft(form);
            setTimeout(function() {
                showAutosaveIndicator("saved");
            }, 300);
        }, AUTOSAVE_DELAY);

        form.addEventListener("input", debouncedSave);
        form.addEventListener("change", debouncedSave);

        // Clear draft on successful form submission
        form.addEventListener("submit", function () {
            clearDraft(form);
        });
    }

    // Find and initialize all auto-save forms
    function setupAutoSave() {
        var forms = document.querySelectorAll("form[data-autosave]");
        forms.forEach(initAutoSave);
    }

    // Run on page load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupAutoSave);
    } else {
        setupAutoSave();
    }
})();

// --- Unsaved Changes Warning ---
(function() {
    var formDirty = false;

    function markFormDirty() {
        formDirty = true;
    }

    function markFormClean() {
        formDirty = false;
    }

    function setupUnsavedWarning() {
        // Track changes on forms with data-autosave attribute
        var forms = document.querySelectorAll("form[data-autosave]");
        forms.forEach(function(form) {
            form.addEventListener("input", markFormDirty);
            form.addEventListener("change", markFormDirty);
            form.addEventListener("submit", markFormClean);
        });

        // Warn before leaving page with unsaved changes
        window.addEventListener("beforeunload", function(e) {
            if (formDirty) {
                e.preventDefault();
                e.returnValue = ""; // Required for Chrome
                return t("unsavedWarning", "You have unsaved changes. Are you sure you want to leave?");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupUnsavedWarning);
    } else {
        setupUnsavedWarning();
    }
})();

// --- Modal Focus Trap (A11Y-2 — WCAG 2.4.3) ---
// Traps keyboard focus inside modal dialogs so Tab/Shift+Tab cycle within the modal
(function() {
    var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function trapFocus(modal) {
        var focusableEls = modal.querySelectorAll(FOCUSABLE);
        if (focusableEls.length === 0) return;

        var firstEl = focusableEls[0];
        var lastEl = focusableEls[focusableEls.length - 1];

        function handleTab(e) {
            if (e.key !== "Tab") return;

            if (e.shiftKey) {
                // Shift+Tab: if on first element, wrap to last
                if (document.activeElement === firstEl || document.activeElement === modal) {
                    e.preventDefault();
                    lastEl.focus();
                }
            } else {
                // Tab: if on last element, wrap to first
                if (document.activeElement === lastEl) {
                    e.preventDefault();
                    firstEl.focus();
                }
            }
        }

        modal._focusTrapHandler = handleTab;
        modal.addEventListener("keydown", handleTab);
    }

    function releaseFocus(modal) {
        if (modal._focusTrapHandler) {
            modal.removeEventListener("keydown", modal._focusTrapHandler);
            delete modal._focusTrapHandler;
        }
    }

    // Observe modal visibility changes via MutationObserver
    function watchModal(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;

        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === "hidden") {
                    if (!modal.hidden) {
                        trapFocus(modal);
                    } else {
                        releaseFocus(modal);
                    }
                }
            });
        });
        observer.observe(modal, { attributes: true, attributeFilter: ["hidden"] });
    }

    function setup() {
        watchModal("shortcuts-modal");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
})();

// --- Keyboard Shortcuts ---
(function() {
    var pendingKey = null;
    var pendingTimeout = null;
    var lastFocusedElement = null;

    function isInputFocused() {
        var active = document.activeElement;
        if (!active) return false;
        var tag = active.tagName.toLowerCase();
        return tag === "input" || tag === "textarea" || tag === "select" || active.isContentEditable;
    }

    function showShortcutsModal() {
        var modal = document.getElementById("shortcuts-modal");
        var backdrop = document.getElementById("shortcuts-backdrop");
        if (modal && backdrop) {
            lastFocusedElement = document.activeElement;
            modal.hidden = false;
            backdrop.hidden = false;
            modal.focus();
        }
    }

    function hideShortcutsModal() {
        var modal = document.getElementById("shortcuts-modal");
        var backdrop = document.getElementById("shortcuts-backdrop");
        if (modal && backdrop) {
            modal.hidden = true;
            backdrop.hidden = true;
            // Return focus to the element that opened the modal
            if (lastFocusedElement && lastFocusedElement.focus) {
                lastFocusedElement.focus();
                lastFocusedElement = null;
            }
        }
    }

    function handleShortcut(key) {
        // Two-key sequences (g + something)
        if (pendingKey === "g") {
            pendingKey = null;
            clearTimeout(pendingTimeout);

            if (key === "h") {
                // g h = Go to Home
                window.location.href = "/";
                return true;
            }
            return false;
        }

        // Single key shortcuts
        switch (key) {
            case "/":
                // Focus search input
                var search = document.querySelector("input[name='q'], input[type='search'], .search-input-wrapper input");
                if (search) {
                    search.focus();
                    search.select();
                    return true;
                }
                break;

            case "g":
                // Start g-sequence
                pendingKey = "g";
                pendingTimeout = setTimeout(function() {
                    pendingKey = null;
                }, 1000);
                return true;

            case "n":
                // New quick note (only on client page)
                var quickNoteLink = document.querySelector("a[href*='quick-note']");
                if (quickNoteLink) {
                    quickNoteLink.click();
                    return true;
                }
                break;

            case "?":
                showShortcutsModal();
                return true;
        }

        return false;
    }

    function setupKeyboardShortcuts() {
        document.addEventListener("keydown", function(e) {
            // Don't intercept shortcuts when typing in inputs
            if (isInputFocused() && e.key !== "Escape") {
                return;
            }

            // Escape closes modals
            if (e.key === "Escape") {
                hideShortcutsModal();
                return;
            }

            // Ctrl+S to save form
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                var form = document.querySelector("form[data-autosave]");
                if (form) {
                    e.preventDefault();
                    form.requestSubmit ? form.requestSubmit() : form.submit();
                    return;
                }
            }

            // Don't process if modifier keys are held (except for Ctrl+S above)
            if (e.ctrlKey || e.metaKey || e.altKey) {
                return;
            }

            if (handleShortcut(e.key)) {
                e.preventDefault();
            }
        });

        // Button to show shortcuts modal
        var showBtn = document.getElementById("show-shortcuts");
        if (showBtn) {
            showBtn.addEventListener("click", showShortcutsModal);
        }

        // Close shortcuts modal
        var closeBtn = document.getElementById("close-shortcuts");
        if (closeBtn) {
            closeBtn.addEventListener("click", hideShortcutsModal);
        }

        // Close modal when clicking backdrop
        var backdrop = document.getElementById("shortcuts-backdrop");
        if (backdrop) {
            backdrop.addEventListener("click", hideShortcutsModal);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupKeyboardShortcuts);
    } else {
        setupKeyboardShortcuts();
    }
})();

// --- Session Timer ---
// Hidden by default. Only shows a warning when login is about to expire.
(function() {
    var WARNING_THRESHOLD = 5; // minutes — show warning
    var CRITICAL_THRESHOLD = 1; // minutes — urgent warning

    function setupSessionTimer() {
        var timerEl = document.getElementById("session-timer");
        var messageEl = document.getElementById("session-message");
        var extendBtn = document.getElementById("extend-session");
        if (!timerEl || !messageEl) return;

        var timeoutMinutes = parseInt(timerEl.getAttribute("data-timeout"), 10) || 30;
        var warnTemplate = timerEl.getAttribute("data-warn") || "Your login expires in {mins} minute(s)";
        var urgentTemplate = timerEl.getAttribute("data-urgent") || "You'll be logged out in {mins} minute(s)";
        var remainingSeconds = timeoutMinutes * 60;

        function formatMessage(template, mins) {
            return template.replace("{mins}", mins);
        }

        function updateDisplay() {
            var mins = Math.floor(remainingSeconds / 60);

            timerEl.classList.remove("warning", "critical");

            if (mins <= CRITICAL_THRESHOLD) {
                timerEl.hidden = false;
                timerEl.classList.add("critical");
                messageEl.textContent = formatMessage(urgentTemplate, mins);
                if (extendBtn) extendBtn.hidden = false;
            } else if (mins <= WARNING_THRESHOLD) {
                timerEl.hidden = false;
                timerEl.classList.add("warning");
                messageEl.textContent = formatMessage(warnTemplate, mins);
                if (extendBtn) extendBtn.hidden = false;
            } else {
                // Plenty of time — hide everything
                timerEl.hidden = true;
                if (extendBtn) extendBtn.hidden = true;
            }
        }

        function tick() {
            remainingSeconds--;
            if (remainingSeconds <= 0) {
                // Session expired — reload to trigger login redirect
                window.location.reload();
                return;
            }
            updateDisplay();
        }

        // Reset timer on user activity
        function resetTimer() {
            remainingSeconds = timeoutMinutes * 60;
            updateDisplay();
        }

        // Track user activity to reset timer
        var activityEvents = ["mousedown", "keydown", "scroll", "touchstart"];
        var resetDebounced = debounce(resetTimer, 1000);
        activityEvents.forEach(function(evt) {
            document.addEventListener(evt, resetDebounced, { passive: true });
        });

        // "Stay logged in" button — resets the timer explicitly
        if (extendBtn) {
            extendBtn.addEventListener("click", function() {
                resetTimer();
            });
        }

        // Simple debounce for activity tracking
        function debounce(fn, delay) {
            var timer = null;
            return function() {
                clearTimeout(timer);
                timer = setTimeout(fn, delay);
            };
        }

        // Initial display (hidden — plenty of time)
        updateDisplay();

        // Tick every minute
        setInterval(tick, 60000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupSessionTimer);
    } else {
        setupSessionTimer();
    }
})();

// --- BUG-6: Offline Detection Banner ---
// Shows a warning when the browser loses network connectivity
(function () {
    function setupOfflineDetection() {
        var banner = document.getElementById("offline-banner");
        if (!banner) return;

        window.addEventListener("offline", function () {
            banner.hidden = false;
        });

        window.addEventListener("online", function () {
            banner.hidden = true;
        });

        // "Try again" button
        var retryBtn = banner.querySelector(".offline-retry");
        if (retryBtn) {
            retryBtn.addEventListener("click", function () {
                window.location.reload();
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupOfflineDetection);
    } else {
        setupOfflineDetection();
    }
})();
