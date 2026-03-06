/* KoNote Web — minimal vanilla JS for interactions */

// Translated strings helper — reads from window.KN (set in base.html)
// Falls back to English if KN not loaded
var KN = window.KN || {};
function t(key, fallback) {
    return KN[key] || fallback;
}

function _knParseCallArgs(raw, el) {
    if (!raw) return [];
    try {
        var parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];
        return parsed.map(function (item) {
            return item === "$el" ? el : item;
        });
    } catch (err) {
        console.warn("Invalid data-call-args JSON", err);
        return [];
    }
}

function _knCallFunction(name, el, rawArgs) {
    if (!name || typeof window[name] !== "function") return false;
    var args = _knParseCallArgs(rawArgs, el);
    window[name].apply(window, args);
    return true;
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

// --- Auto-focus form error summary on page load (BUG-23 — WCAG 3.3.1) ---
// When a form has validation errors, move focus to the error summary
// so keyboard/screen reader users know the form failed
(function () {
    function enableDateYearShortcut() {
        var dateInputs = document.querySelectorAll('input[type="date"][data-year-shortcut="true"]');
        dateInputs.forEach(function (input) {
            input.addEventListener("input", function (event) {
                var raw = (event.target.value || "").trim();
                if (/^\d{4}$/.test(raw)) {
                    event.target.value = raw + "-01-01";
                }
            });
            input.addEventListener("blur", function (event) {
                var raw = (event.target.value || "").trim();
                if (/^\d{4}$/.test(raw)) {
                    event.target.value = raw + "-01-01";
                }
            });
        });
    }

    function focusErrorSummary() {
        var summary = document.getElementById("form-error-summary");
        if (summary) {
            summary.focus();
        }
        enableDateYearShortcut();
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", focusErrorSummary);
    } else {
        focusErrorSummary();
    }
})();

// --- Link form error messages to their inputs (aria-describedby) ---
// Scans for <small class="error"> and links the preceding input/select/textarea
(function () {
    function linkErrorMessages() {
        var errors = document.querySelectorAll("small.error");
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
                    // Ensure error element has an ID for aria-describedby
                    if (!errorEl.id) {
                        errorEl.id = "error-" + Math.random().toString(36).substr(2, 9);
                    }
                    var existing = input.getAttribute("aria-describedby");
                    if (existing) {
                        if (existing.indexOf(errorEl.id) === -1) {
                            input.setAttribute("aria-describedby", existing + " " + errorEl.id);
                        }
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

    // Also run after HTMX swaps so dynamic form errors are linked
    document.body.addEventListener("htmx:afterSwap", linkErrorMessages);
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

// --- Unified "Copy to Clipboard" utility ---
// Attaches a click handler to any element with the class "copy-btn"
(function () {
    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".copy-btn");
        if (!btn) return;
        e.preventDefault();

        var textToCopy = "";

        // 1. Direct text via data attribute
        if (btn.hasAttribute("data-clipboard-text")) {
            textToCopy = btn.getAttribute("data-clipboard-text");
        }
        // 2. Read from a target element (input value or text content)
        else if (btn.hasAttribute("data-clipboard-target")) {
            var targetSelector = btn.getAttribute("data-clipboard-target");
            // If it doesn't start with # or ., assume it's an ID
            if (!targetSelector.startsWith("#") && !targetSelector.startsWith(".")) {
                targetSelector = "#" + targetSelector;
            }
            var targetEl = document.querySelector(targetSelector);
            if (targetEl) {
                textToCopy = targetEl.tagName === "INPUT" || targetEl.tagName === "TEXTAREA"
                    ? targetEl.value
                    : targetEl.textContent;
            }
        }
        // 3. Read from the closest ancestor matching a selector
        else if (btn.hasAttribute("data-clipboard-closest")) {
            var closestSelector = btn.getAttribute("data-clipboard-closest");
            var sourceEl = btn.closest(closestSelector);
            if (sourceEl) {
                textToCopy = sourceEl.innerText || sourceEl.textContent || "";
            }
        }

        if (!textToCopy) return;

        // Perform the copy
        navigator.clipboard.writeText(textToCopy).then(function () {
            // Visual feedback
            var originalText = btn.innerHTML;
            // Use translation if available, fallback to "Copied!"
            btn.textContent = t("copied", "Copied!");

            // Temporary success styling
            var originalColor = btn.style.color;
            var originalBorder = btn.style.borderColor;
            btn.style.color = "var(--kn-success-fg, #10B981)";
            btn.style.borderColor = "var(--kn-success-fg, #10B981)";

            setTimeout(function () {
                btn.innerHTML = originalText;
                btn.style.color = originalColor;
                btn.style.borderColor = originalBorder;
            }, 2000);
        }).catch(function (err) {
            console.error("Failed to copy: ", err);
        });
    });
})();

// --- Generic delegated UI helpers for CSP-safe templates ---
(function () {
    document.addEventListener("click", function (event) {
        var target = event.target.closest(
            "[data-reload-page],[data-print-page],[data-select-on-click],[data-confirm],[data-call-function],[data-dismiss-closest],[data-set-value-target]"
        );
        if (!target) return;

        if (target.hasAttribute("data-confirm")) {
            var message = target.getAttribute("data-confirm") || "";
            if (!window.confirm(message)) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
        }

        if (target.hasAttribute("data-reload-page")) {
            event.preventDefault();
            window.location.reload();
            return;
        }

        if (target.hasAttribute("data-print-page")) {
            event.preventDefault();
            window.print();
            return;
        }

        if (target.hasAttribute("data-select-on-click")) {
            if (typeof target.select === "function") {
                target.select();
            }
            return;
        }

        if (target.hasAttribute("data-dismiss-closest")) {
            event.preventDefault();
            var selector = target.getAttribute("data-dismiss-closest");
            var mode = target.getAttribute("data-dismiss-mode") || "remove";
            var dismissTarget = target.closest(selector);
            if (dismissTarget) {
                if (mode === "clear") dismissTarget.innerHTML = "";
                else dismissTarget.remove();
            }
            return;
        }

        if (target.hasAttribute("data-call-function")) {
            var prevent = target.getAttribute("data-prevent-default");
            if (prevent !== "false") {
                event.preventDefault();
            }
            _knCallFunction(
                target.getAttribute("data-call-function"),
                target,
                target.getAttribute("data-call-args")
            );
            return;
        }

        if (target.hasAttribute("data-set-value-target")) {
            var clickValueTargetSelector = target.getAttribute("data-set-value-target");
            if (!clickValueTargetSelector.startsWith("#") && !clickValueTargetSelector.startsWith(".")) {
                clickValueTargetSelector = "#" + clickValueTargetSelector;
            }
            var clickValueTarget = document.querySelector(clickValueTargetSelector);
            if (clickValueTarget) {
                clickValueTarget.value = target.getAttribute("data-set-value") || "";
            }
        }
    });

    document.addEventListener("change", function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) return;

        if (target.matches("[data-submit-on-change]")) {
            if (target.form) target.form.submit();
        }

        if (target.matches("[data-toggle-display-target]")) {
            var toggleTarget = document.getElementById(target.getAttribute("data-toggle-display-target"));
            var expectedValue = target.getAttribute("data-toggle-display-value") || "";
            if (toggleTarget) {
                toggleTarget.style.display = target.value === expectedValue ? "" : "none";
            }
        }

        if (target.matches("[data-set-value-target]")) {
            var valueTarget = document.querySelector(target.getAttribute("data-set-value-target"));
            if (valueTarget) {
                valueTarget.value = target.value;
            }
        }

        if (target.matches("[data-call-function-on-change]")) {
            _knCallFunction(
                target.getAttribute("data-call-function-on-change"),
                target,
                target.getAttribute("data-call-args")
            );
        }
    });

    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        var message = form.getAttribute("data-confirm");
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });
})();

// --- Screen reader announcer for HTMX form success (IMPROVE-9) ---
// When an HTMX POST succeeds, announce "Saved" to screen readers via #sr-announcer
(function () {
    var announcer = document.getElementById("sr-announcer");
    if (!announcer) return;

    document.body.addEventListener("htmx:afterRequest", function (event) {
        var verb = (event.detail.requestConfig && event.detail.requestConfig.verb) || "";
        if (verb.toLowerCase() === "post" && event.detail.successful) {
            announcer.textContent = "";
            // Small delay so aria-live picks up the change
            setTimeout(function () {
                announcer.textContent = t("saved", "Saved");
            }, 100);
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
    } else if (status === 429) {
        message = t("rate_limited", "Too many requests. Please wait a few minutes before trying again.");
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

// --- Success toast for async confirmations (UXP2 / WCAG 4.1.3) ---
// Triggered by HX-Trigger: {"showSuccess": "message"} from Django views
document.body.addEventListener("showSuccess", function (e) {
    var msg = (e.detail && e.detail.value) || e.detail || "";
    var toast = document.getElementById("htmx-success-toast");
    if (toast) {
        var msgEl = document.getElementById("htmx-success-toast-message");
        if (msgEl) { msgEl.textContent = msg; }
        toast.hidden = false;
        // Auto-dismiss after 4 seconds (success messages are confirmatory)
        setTimeout(function () { toast.hidden = true; }, 4000);
    }
    // Announce to screen readers via aria-live region
    var announcer = document.getElementById("sr-announcer");
    if (announcer) {
        announcer.textContent = "";
        setTimeout(function () { announcer.textContent = msg; }, 100);
    }
});

// Close button for success toast
document.addEventListener("click", function (event) {
    if (event.target && event.target.id === "htmx-success-toast-close") {
        var toast = document.getElementById("htmx-success-toast");
        if (toast) { toast.hidden = true; }
    }
});

// --- Filter button aria-pressed toggle (UXP5 / WCAG 4.1.2) ---
// Updates aria-pressed and visual state when filter buttons are clicked
document.body.addEventListener("click", function (e) {
    var btn = e.target.closest("[aria-pressed]");
    if (btn) {
        var group = btn.closest("[role='group']");
        if (group && group.querySelector(".filter-btn")) {
            group.querySelectorAll("[aria-pressed]").forEach(function (b) {
                b.setAttribute("aria-pressed", "false");
                b.classList.remove("filter-active");
            });
            btn.setAttribute("aria-pressed", "true");
            btn.classList.add("filter-active");
        }
    }
});

// Screen reader loading announcement for HTMX search (BLOCKER-1 / WCAG 4.1.3)
// Announces "Loading..." when search starts and "Results loaded" when done
(function () {
    var statusEl = document.getElementById("search-status");
    if (!statusEl) return;

    document.body.addEventListener("htmx:beforeRequest", function (event) {
        if (event.detail.target && event.detail.target.id === "client-list-container") {
            statusEl.textContent = t("loading", "Loading\u2026");
        }
    });
    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.detail.target && event.detail.target.id === "client-list-container") {
            statusEl.textContent = t("resultsLoaded", "Results loaded.");
        }
    });
})();

// Focus management for note detail expansion (accessibility)
// When a note card expands via HTMX, move focus to the detail content
// Use preventScroll so the page doesn't jump when expanding/collapsing notes
document.body.addEventListener("htmx:afterSwap", function (event) {
    var detail = event.detail.target.querySelector(".note-detail-content");
    if (detail) {
        detail.focus({ preventScroll: true });
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

// Block interactions on aria-disabled="true" buttons (WCAG 4.1.2)
// Unlike the HTML `disabled` attribute, aria-disabled keeps the element in the
// tab order (so keyboard users can reach and read it) but does not block events.
// These listeners ensure no action fires when the user clicks or presses Enter/Space.
document.addEventListener("click", function (e) {
    var btn = e.target.closest("button[aria-disabled='true']");
    if (btn) { e.preventDefault(); e.stopPropagation(); }
});
document.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") &&
        e.target.getAttribute("aria-disabled") === "true" &&
        e.target.tagName === "BUTTON") {
        e.preventDefault();
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

// --- Tab bar: arrow key navigation for ARIA tablist (BUG-14 / QA-R8-A11Y8 — WCAG 2.1.1) ---
// Left/Right arrow keys move focus between tabs; Home/End jump to first/last.
// WAI-ARIA roving tabindex: only the active tab is in the natural tab order
// (tabindex="0"); all others use tabindex="-1" so Tab skips them.
// This prevents ArrowRight on a tab from accidentally triggering the adjacent
// Actions dropdown (aria-haspopup="menu") via AT toolbar navigation.
(function () {
    function initTabindexes(tabs) {
        // Set roving tabindex: active tab = 0, all others = -1
        tabs.forEach(function (tab) {
            var isActive = tab.getAttribute("aria-selected") === "true" ||
                           tab.classList.contains("tab-active");
            tab.setAttribute("tabindex", isActive ? "0" : "-1");
        });
    }

    function setupTablistKeyboard() {
        var tabBar = document.querySelector("[role='tablist']");
        if (!tabBar) return;

        // Guard: only attach the listener once (re-called after HTMX swaps)
        if (tabBar.dataset.kbReady) return;
        tabBar.dataset.kbReady = "1";

        // Initialise roving tabindex on page load
        var tabs = Array.from(tabBar.querySelectorAll("[role='tab']"));
        initTabindexes(tabs);

        tabBar.addEventListener("keydown", function (e) {
            var tabs = Array.from(tabBar.querySelectorAll("[role='tab']"));
            if (!tabs.length) return;
            var current = tabs.indexOf(document.activeElement);
            if (current === -1) return;
            var next;
            if (e.key === "ArrowRight" || e.key === "ArrowDown") {
                next = current < tabs.length - 1 ? current + 1 : 0;
            } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
                next = current > 0 ? current - 1 : tabs.length - 1;
            } else if (e.key === "Home") {
                next = 0;
            } else if (e.key === "End") {
                next = tabs.length - 1;
            } else {
                return;
            }
            e.preventDefault();
            e.stopPropagation(); // prevent Actions dropdown toolbar from seeing the arrow key
            // Update roving tabindex before moving focus
            tabs.forEach(function (t) { t.setAttribute("tabindex", "-1"); });
            tabs[next].setAttribute("tabindex", "0");
            tabs[next].focus();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupTablistKeyboard);
    } else {
        setupTablistKeyboard();
    }
    document.body.addEventListener("htmx:afterSettle", function () {
        // Reset guard after HTMX replaces the tab bar DOM so re-init works
        var tabBar = document.querySelector("[role='tablist']");
        if (tabBar) { delete tabBar.dataset.kbReady; }
        setupTablistKeyboard();
    });
})();

// --- Tab bar: scroll active tab into view + edge fade indicators ---
(function () {
    function setupTabBar() {
        var tabBar = document.querySelector(".tab-bar");
        if (!tabBar) return;

        // Scroll the active tab into view (centred) on mobile
        var activeTab = tabBar.querySelector(".tab-active, [aria-current='page']");
        if (activeTab) {
            activeTab.scrollIntoView({ inline: "center", block: "nearest", behavior: "instant" });
        }

        // Update edge fade classes based on scroll position
        var nav = tabBar.closest("nav");
        if (!nav) return;

        function updateFades() {
            var scrollLeft = tabBar.scrollLeft;
            var maxScroll = tabBar.scrollWidth - tabBar.clientWidth;
            nav.classList.toggle("fade-left", scrollLeft > 4);
            nav.classList.toggle("fade-right", scrollLeft < maxScroll - 4);
        }

        tabBar.addEventListener("scroll", updateFades, { passive: true });
        updateFades();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupTabBar);
    } else {
        setupTabBar();
    }
    // Re-run after HTMX tab swap so fades update
    document.body.addEventListener("htmx:afterSettle", function (e) {
        if (e.detail.target && e.detail.target.id === "tab-content") {
            setupTabBar();
        }
    });
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
            if (key === "m") {
                // g m = Go to Meetings
                window.location.href = "/events/meetings/";
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

// --- Actions dropdown toggle ---
// Opens/closes the ▾ More menu on the participant detail page
// Supports: click toggle, click-outside-close, Escape, arrow-key navigation
(function () {
    function closeAllDropdowns() {
        document.querySelectorAll(".actions-dropdown-menu").forEach(function (m) {
            m.hidden = true;
            var btn = m.previousElementSibling;
            if (btn) btn.setAttribute("aria-expanded", "false");
        });
    }

    function getMenuItems(menu) {
        return Array.from(menu.querySelectorAll('[role="menuitem"]'));
    }

    function setupActionsDropdown() {
        document.addEventListener("click", function (e) {
            var toggle = e.target.closest(".actions-dropdown-toggle");
            if (toggle) {
                e.stopPropagation();
                var menu = toggle.nextElementSibling;
                if (!menu) return;
                var isOpen = !menu.hidden;
                closeAllDropdowns();
                if (!isOpen) {
                    menu.hidden = false;
                    toggle.setAttribute("aria-expanded", "true");
                    // Focus first menu item on open
                    var items = getMenuItems(menu);
                    if (items.length) items[0].focus();
                }
                return;
            }
            // Click outside closes all dropdowns
            closeAllDropdowns();
        });

        document.addEventListener("keydown", function (e) {
            // Escape closes dropdowns and returns focus to trigger
            if (e.key === "Escape") {
                document.querySelectorAll(".actions-dropdown-menu:not([hidden])").forEach(function (m) {
                    m.hidden = true;
                    var btn = m.previousElementSibling;
                    if (btn) {
                        btn.setAttribute("aria-expanded", "false");
                        btn.focus();
                    }
                });
                return;
            }

            // Arrow-key navigation within open menu
            var openMenu = document.querySelector(".actions-dropdown-menu:not([hidden])");
            if (!openMenu) return;
            if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "Home" && e.key !== "End") return;
            e.preventDefault();
            var items = getMenuItems(openMenu);
            if (!items.length) return;
            var current = items.indexOf(document.activeElement);
            var next;
            if (e.key === "ArrowDown") {
                next = current < items.length - 1 ? current + 1 : 0;
            } else if (e.key === "ArrowUp") {
                next = current > 0 ? current - 1 : items.length - 1;
            } else if (e.key === "Home") {
                next = 0;
            } else if (e.key === "End") {
                next = items.length - 1;
            }
            items[next].focus();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupActionsDropdown);
    } else {
        setupActionsDropdown();
    }
})();

// --- Confirmation dialog for PII exports ---
// Links with class "actions-confirm" show a confirm dialog before navigating
(function () {
    document.addEventListener("click", function (e) {
        var link = e.target.closest(".actions-confirm");
        if (!link) return;
        var message = link.getAttribute("data-confirm-message") || t("confirmExport", "This will export personal information. Continue?");
        if (!confirm(message)) {
            e.preventDefault();
        }
    });
})();

// --- Inline Quick Note progressive disclosure ---
// Shows/hides outcome and consent fields based on interaction type selection
(function () {
    var CONTACT_TYPES = ["phone", "sms", "email"];
    var CONSENT_TYPES = ["session", "home_visit"];

    function setupInlineQuickNote(container) {
        var form = container.querySelector("#inline-quick-note-form");
        if (!form) return;

        var radios = form.querySelectorAll("[name='interaction_type']");
        var outcomeGroup = container.querySelector("#inline-outcome-group");
        var consentGroup = container.querySelector("#inline-consent-group");
        var outcomeSelect = form.querySelector("[name='outcome']");

        function updateVisibility() {
            var selected = form.querySelector("[name='interaction_type']:checked");
            if (!selected) return;
            var type = selected.value;
            var isContact = CONTACT_TYPES.indexOf(type) !== -1;

            // Show/hide outcome for contact types
            if (outcomeGroup) {
                outcomeGroup.hidden = !isContact;
                if (!isContact && outcomeSelect) {
                    outcomeSelect.value = "";
                }
            }

            // Show/hide consent:
            // - Always for session/home_visit
            // - For contacts, only when outcome is "reached"
            if (consentGroup) {
                var outcome = outcomeSelect ? outcomeSelect.value : "";
                var showConsent = CONSENT_TYPES.indexOf(type) !== -1 ||
                    (isContact && outcome === "reached");
                consentGroup.hidden = !showConsent;
            }
        }

        radios.forEach(function (r) {
            r.addEventListener("change", updateVisibility);
        });
        if (outcomeSelect) {
            outcomeSelect.addEventListener("change", updateVisibility);
        }
        updateVisibility();
    }

    // Run after HTMX swaps the inline form into the page
    document.body.addEventListener("htmx:afterSwap", function (event) {
        var container = event.detail.target;
        if (container && container.querySelector("#inline-quick-note-form")) {
            setupInlineQuickNote(container);
        }
    });
})();

// --- Focus management: after marking a message read, focus next unread ---
// Uses htmx:afterSettle (not afterSwap) so the DOM is stable after outerHTML replacement
document.body.addEventListener("htmx:afterSettle", function (event) {
    var settled = event.detail.target;
    if (!settled || !settled.classList || !settled.classList.contains("message-card")) return;
    // Find the next unread message card (one with a Mark as Read button)
    var next = settled.nextElementSibling;
    while (next && !next.querySelector("button[type='submit']")) {
        next = next.nextElementSibling;
    }
    if (next) {
        next.setAttribute("tabindex", "-1");
        next.focus();
    }
});

// --- Relative timestamps for <time> elements ---
// Updates elements with data-relative attribute to show "2 hours ago" etc.
// Falls back to absolute date if JS disabled (server renders it).
(function () {
    function updateRelativeTimes() {
        var times = document.querySelectorAll("time[data-relative]");
        var now = Date.now();
        times.forEach(function (el) {
            var dt = new Date(el.getAttribute("datetime"));
            if (isNaN(dt)) return;
            var diff = Math.floor((now - dt) / 1000);
            var text;
            if (diff < 60) text = t("just_now", "just now");
            else if (diff < 3600) {
                var m = Math.floor(diff / 60);
                text = m === 1 ? t("one_min_ago", "1 minute ago") : m + " " + t("mins_ago", "minutes ago");
            } else if (diff < 86400) {
                var h = Math.floor(diff / 3600);
                text = h === 1 ? t("one_hour_ago", "1 hour ago") : h + " " + t("hours_ago", "hours ago");
            } else if (diff < 604800) {
                var d = Math.floor(diff / 86400);
                text = d === 1 ? t("one_day_ago", "1 day ago") : d + " " + t("days_ago", "days ago");
            } else {
                return; // older than 7 days — keep absolute date
            }
            el.textContent = text;
        });
    }
    updateRelativeTimes();
    setInterval(updateRelativeTimes, 60000);
    document.body.addEventListener("htmx:afterSwap", updateRelativeTimes);
})();

// --- Analysis chart: unify quick-select buttons with date picker form (UX-CHART1) ---
// Quick-select buttons set a hidden timeframe input and submit the form;
// manual date inputs clear the timeframe so the two controls don't conflict.
(function () {
    document.body.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-timeframe]");
        if (!btn) return;
        var form = btn.closest("form");
        if (!form) return;
        var hidden = form.querySelector("#id_timeframe");
        if (hidden) hidden.value = btn.getAttribute("data-timeframe");
        // Clear manual date inputs — quick-select overrides them
        var dateFrom = form.querySelector("input[name='date_from']");
        var dateTo = form.querySelector("input[name='date_to']");
        if (dateFrom) dateFrom.value = "";
        if (dateTo) dateTo.value = "";
        form.submit();
    });

    // When a manual date is entered, clear the timeframe so dates take priority
    document.body.addEventListener("change", function (e) {
        if (e.target.name !== "date_from" && e.target.name !== "date_to") return;
        var form = e.target.closest("form");
        if (!form) return;
        var hidden = form.querySelector("#id_timeframe");
        if (hidden) hidden.value = "";
    });
})();

// --- Onboarding banner (QA-W19) ---
// Shows a "Getting started" banner on the dashboard for first-time users.
// Dismissed permanently via localStorage.
(function () {
    var banner = document.getElementById("onboarding-banner");
    var btn = document.getElementById("dismiss-onboarding");
    if (!banner || !btn) return;
    var KEY = "konote_onboarding_dismissed";
    try {
        if (localStorage.getItem(KEY)) return; // already dismissed
    } catch (e) { return; }
    banner.hidden = false;
    btn.addEventListener("click", function () {
        banner.hidden = true;
        try { localStorage.setItem(KEY, "1"); } catch (e) { /* ignore */ }
    });
})();

// --- Bulk Operations (UX17) ---
// Checkbox selection, action bar visibility, and modal management for
// bulk status change and program transfer on the client list.
(function () {
    var selectedIds = new Set();
    var previousFocus = null;  // Store focus before modal opens

    function getBar() { return document.getElementById("bulk-action-bar"); }
    function getCount() { return document.getElementById("bulk-count"); }
    function getBackdrop() { return document.getElementById("bulk-modal-backdrop"); }
    function getModal() { return document.getElementById("bulk-modal-container"); }

    function updateBar() {
        var bar = getBar();
        if (!bar) return;
        var count = selectedIds.size;
        if (count > 0) {
            bar.hidden = false;
            var countEl = getCount();
            if (countEl) {
                // Show "X selected on this page" when paginated
                var totalEl = document.querySelector("[data-total-clients]");
                var total = totalEl ? parseInt(totalEl.getAttribute("data-total-clients"), 10) : 0;
                var visibleCbs = document.querySelectorAll(".bulk-select-row").length;
                if (total > visibleCbs) {
                    countEl.textContent = count + " " + t("selected", "selected")
                        + " (" + t("on this page", "on this page") + ")";
                } else {
                    countEl.textContent = count + " " + t("selected", "selected");
                }
            }
        } else {
            bar.hidden = true;
        }
    }

    // Inject selected IDs into HTMX requests from bulk action buttons
    function injectIds(event) {
        var elt = event.detail.elt;
        if (!elt) return;
        if (elt.id !== "bulk-status-btn" && elt.id !== "bulk-transfer-btn") return;
        // Add client_ids[] parameters to the request
        var params = event.detail.parameters;
        if (!params) return;
        selectedIds.forEach(function (id) {
            if (!params["client_ids[]"]) {
                params["client_ids[]"] = [];
            }
            if (Array.isArray(params["client_ids[]"])) {
                params["client_ids[]"].push(id);
            } else {
                params["client_ids[]"] = [params["client_ids[]"], id];
            }
        });
    }

    function showModal() {
        previousFocus = document.activeElement;
        var backdrop = getBackdrop();
        var modal = getModal();
        if (backdrop) backdrop.hidden = false;
        if (modal) {
            modal.hidden = false;
            // Focus first interactive element inside the modal
            var firstField = modal.querySelector("select, input:not([type='hidden']), textarea, button");
            if (firstField) {
                firstField.focus();
            } else {
                modal.focus();
            }
        }
    }

    // Global function for the Cancel button in confirmation templates
    window.closeBulkModal = function () {
        var backdrop = getBackdrop();
        var modal = getModal();
        if (backdrop) backdrop.hidden = true;
        if (modal) {
            modal.hidden = true;
            modal.innerHTML = "";
        }
        // Restore focus to the element that opened the modal
        if (previousFocus && previousFocus.focus) {
            previousFocus.focus();
            previousFocus = null;
        }
    };

    // Focus trap — keep Tab cycling within the open modal
    function trapFocus(e) {
        var modal = getModal();
        if (!modal || modal.hidden) return;
        if (e.key !== "Tab") return;
        var focusable = modal.querySelectorAll(
            "select, input:not([type='hidden']), textarea, button, [tabindex]:not([tabindex='-1'])"
        );
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    function setupCheckboxes() {
        // Support multiple select-all checkboxes (one per table section).
        // Each scopes to its own <table> so checking "select all" in one
        // section doesn't affect the other.
        var selectAlls = document.querySelectorAll(".bulk-select-all");
        selectAlls.forEach(function (selectAll) {
            selectAll.addEventListener("change", function () {
                var checked = selectAll.checked;
                var table = selectAll.closest("table");
                var rowCbs = table
                    ? table.querySelectorAll(".bulk-select-row")
                    : document.querySelectorAll(".bulk-select-row");
                rowCbs.forEach(function (cb) {
                    cb.checked = checked;
                    if (checked) {
                        selectedIds.add(cb.value);
                    } else {
                        selectedIds.delete(cb.value);
                    }
                });
                updateBar();
            });
        });

        // Delegate click events for row checkboxes
        document.addEventListener("change", function (e) {
            if (!e.target.classList.contains("bulk-select-row")) return;
            if (e.target.checked) {
                selectedIds.add(e.target.value);
            } else {
                selectedIds.delete(e.target.value);
                // Uncheck select-all in the same table section
                var table = e.target.closest("table");
                var sa = table
                    ? table.querySelector(".bulk-select-all")
                    : document.querySelector(".bulk-select-all");
                if (sa) sa.checked = false;
            }
            updateBar();
        });
    }

    function setup() {
        setupCheckboxes();

        // Listen for HTMX config to inject selected IDs
        document.body.addEventListener("htmx:configRequest", injectIds);

        // Show modal after HTMX loads the confirmation form
        document.body.addEventListener("htmx:afterSwap", function (event) {
            var target = event.detail.target;
            if (target && target.id === "bulk-modal-container" && target.innerHTML.trim()) {
                showModal();
            }
        });

        // Close modal on backdrop click
        var backdrop = getBackdrop();
        if (backdrop) {
            backdrop.addEventListener("click", window.closeBulkModal);
        }

        // Close modal on Escape key + focus trap
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                var modal = getModal();
                if (modal && !modal.hidden) {
                    window.closeBulkModal();
                }
            }
            trapFocus(e);
        });
    }

    // Re-sync checkboxes after HTMX replaces the table (pagination, filtering)
    document.body.addEventListener("htmx:afterSwap", function (event) {
        var target = event.detail.target;
        if (target && target.id === "client-list-container") {
            // Re-check any checkboxes that were previously selected
            var rowCbs = target.querySelectorAll(".bulk-select-row");
            rowCbs.forEach(function (cb) {
                if (selectedIds.has(cb.value)) {
                    cb.checked = true;
                }
            });
            // Update select-all state for each table section
            var selectAlls = target.querySelectorAll(".bulk-select-all");
            selectAlls.forEach(function (sa) {
                var table = sa.closest("table");
                var tableCbs = table
                    ? table.querySelectorAll(".bulk-select-row")
                    : rowCbs;
                if (tableCbs.length > 0) {
                    var allChecked = true;
                    tableCbs.forEach(function (cb) {
                        if (!cb.checked) allChecked = false;
                    });
                    sa.checked = allChecked;
                }
            });
            updateBar();
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
})();


// ── Plausibility warnings for metric values (DQ1 + DQ1-TIER2) ───────

(function () {
    "use strict";

    /**
     * Two-tier plausibility checking:
     *   Tier 2 (very unlikely) — RED, requires TWO confirmations
     *   Tier 1 (warn)          — YELLOW, requires ONE confirmation
     *
     * Tier 2 is checked first. If the value is outside tier-2 bounds,
     * the tier-1 check is skipped (tier-2 is always the wider range).
     */
    function checkPlausibility(input) {
        var warnMin = parseFloat(input.getAttribute("data-warn-min"));
        var warnMax = parseFloat(input.getAttribute("data-warn-max"));
        var vuMin = parseFloat(input.getAttribute("data-very-unlikely-min"));
        var vuMax = parseFloat(input.getAttribute("data-very-unlikely-max"));
        var val = parseFloat(input.value);

        var wrapper = input.closest(".metric-number-input");
        if (!wrapper) return;

        var warningDiv = wrapper.querySelector(".plausibility-warning");
        var confirmedInput = wrapper.querySelector(".plausibility-confirmed-input");

        if (!warningDiv) return;

        if (isNaN(val) || input.value.trim() === "") {
            warningDiv.style.display = "none";
            warningDiv.classList.remove("tier-2");
            warningDiv.removeAttribute("data-confirm-count");
            if (confirmedInput) confirmedInput.value = "";
            return;
        }

        var metricLabel = wrapper.querySelector("label");
        var labelText = metricLabel ? metricLabel.textContent.trim() : "this metric";
        var formattedVal = val.toLocaleString();

        // ── Tier 2: very unlikely ────────────────────────────────────
        var isBelowVU = !isNaN(vuMin) && val < vuMin;
        var isAboveVU = !isNaN(vuMax) && val > vuMax;

        if (isBelowVU || isAboveVU) {
            var warningText = warningDiv.querySelector(".warning-text");
            warningText.textContent = t("plausibility_tier2",
                "This value ({value}) is extremely unlikely for {metric}. This is almost certainly a data-entry error. Please re-check and confirm twice if correct.")
                .replace("{value}", formattedVal).replace("{metric}", labelText);

            warningDiv.style.display = "block";
            warningDiv.classList.add("tier-2");
            warningDiv.setAttribute("aria-live", "assertive");
            // Reset confirmation — tier-2 requires two clicks
            warningDiv.setAttribute("data-confirm-count", "0");
            if (confirmedInput) confirmedInput.value = "";
            var btn = warningDiv.querySelector(".plausibility-confirm-btn");
            if (btn) {
                btn.style.display = "";
                btn.textContent = t("confirm_this_value", "Confirm this value");
            }
            return;
        }

        // ── Tier 1: warn ─────────────────────────────────────────────
        var isBelowWarn = !isNaN(warnMin) && val < warnMin;
        var isAboveWarn = !isNaN(warnMax) && val > warnMax;

        var originalInput = wrapper.querySelector(".plausibility-original-value");

        if (isBelowWarn || isAboveWarn) {
            var warningText = warningDiv.querySelector(".warning-text");

            // Store the original flagged value for override logging
            if (originalInput && !originalInput.value) {
                originalInput.value = val;
            }

            if (isAboveWarn) {
                warningText.textContent = t("plausibility_high",
                    "This value ({value}) is unusually high for {metric}. Please double-check. If correct, click Confirm.")
                    .replace("{value}", formattedVal).replace("{metric}", labelText);
            } else {
                warningText.textContent = t("plausibility_low",
                    "This value ({value}) is unusually low for {metric}. Please double-check. If correct, click Confirm.")
                    .replace("{value}", formattedVal).replace("{metric}", labelText);
            }

            warningDiv.style.display = "block";
            warningDiv.classList.remove("tier-2");
            warningDiv.removeAttribute("data-confirm-count");
            warningDiv.setAttribute("aria-live", "polite");
            // Reset confirmation when value changes
            if (confirmedInput) confirmedInput.value = "";
            // Update original value to reflect the current flagged value
            if (originalInput) originalInput.value = val;
            var btn = warningDiv.querySelector(".plausibility-confirm-btn");
            if (btn) {
                btn.style.display = "";
                btn.textContent = t("confirm_this_value", "Confirm this value");
                warningDiv.style.color = "";
            }
        } else {
            warningDiv.style.display = "none";
            warningDiv.classList.remove("tier-2");
            warningDiv.removeAttribute("data-confirm-count");
            if (confirmedInput) confirmedInput.value = "";
            if (originalInput) originalInput.value = "";
        }
    }

    // Handle confirm button clicks via delegation
    document.addEventListener("click", function (e) {
        if (!e.target.classList.contains("plausibility-confirm-btn")) return;

        var warningDiv = e.target.closest(".plausibility-warning");
        var wrapper = warningDiv ? warningDiv.closest(".metric-number-input") : null;
        if (!wrapper) return;

        var confirmedInput = wrapper.querySelector(".plausibility-confirmed-input");

        // Tier-2: require two confirmations
        if (warningDiv.classList.contains("tier-2")) {
            var count = parseInt(warningDiv.getAttribute("data-confirm-count") || "0", 10);
            count++;
            warningDiv.setAttribute("data-confirm-count", String(count));

            if (count === 1) {
                // First click — change button text, do NOT confirm yet
                e.target.textContent = t("click_again_to_confirm", "Click again to confirm");
                return;
            }
            // Second click — confirmed
        }

        if (confirmedInput) confirmedInput.value = "True";

        var warningText = warningDiv.querySelector(".warning-text");
        if (warningText) warningText.textContent = t("value_confirmed", "Value confirmed.");
        e.target.style.display = "none";
        warningDiv.style.color = "var(--pico-muted-color)";
        warningDiv.classList.remove("tier-2");
        warningDiv.removeAttribute("data-confirm-count");
        warningDiv.setAttribute("aria-live", "polite");
    });

    // Selector matches inputs with any plausibility data attribute
    var plausibilitySelector =
        'input[type="number"][data-warn-min],' +
        'input[type="number"][data-warn-max],' +
        'input[type="number"][data-very-unlikely-min],' +
        'input[type="number"][data-very-unlikely-max]';

    // Check on change and blur for metric number inputs with warn/vu attributes
    document.addEventListener("change", function (e) {
        if (e.target.matches(plausibilitySelector)) {
            checkPlausibility(e.target);
        }
    });
    document.addEventListener("blur", function (e) {
        if (e.target.matches(plausibilitySelector)) {
            checkPlausibility(e.target);
        }
    }, true);

    // Block form submit if unconfirmed plausibility warnings exist
    document.addEventListener("submit", function (e) {
        var warnings = e.target.querySelectorAll('.plausibility-warning[style*="block"]');
        if (!warnings.length) return;

        for (var i = 0; i < warnings.length; i++) {
            var wrapper = warnings[i].closest(".metric-number-input");
            if (!wrapper) continue;
            var confirmed = wrapper.querySelector(".plausibility-confirmed-input");
            if (!confirmed || confirmed.value !== "True") {
                e.preventDefault();
                warnings[i].querySelector(".warning-text").style.fontWeight = "bold";
                warnings[i].scrollIntoView({ behavior: "smooth", block: "center" });
                return;
            }
        }
    });
})();
