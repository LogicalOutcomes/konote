/**
 * Portal JavaScript — quick exit, session timeout warning, banner dismiss.
 */

// Quick exit — immediately leave and destroy session
function quickExit() {
    // Clear any localStorage drafts before leaving (privacy safety)
    try { localStorage.clear(); } catch (e) { /* ignore */ }
    // Best-effort session destruction via sendBeacon
    navigator.sendBeacon('/my/emergency-logout/');
    // Replace current history entry so back button doesn't return here
    window.location.replace('https://www.google.ca');
}

// Dismiss "new since last visit" banner
function dismissBanner() {
    var banner = document.getElementById('new-since-banner');
    if (banner) {
        banner.hidden = true;
    }
}

// Session timeout warning using native <dialog> element
(function() {
    var WARN_AT = 25 * 60 * 1000;  // 25 minutes in ms
    var LOGOUT_AT = 30 * 60 * 1000;  // 30 minutes in ms
    var timer = null;
    var logoutTimer = null;
    var dialog = null;

    function getDialog() {
        if (!dialog) {
            dialog = document.getElementById('session-timeout-dialog');
        }
        return dialog;
    }

    function showWarning() {
        var d = getDialog();
        if (d && typeof d.showModal === 'function' && !d.open) {
            d.showModal();
            // Focus the "I'm still here" button
            var btn = document.getElementById('timeout-stay-btn');
            if (btn) btn.focus();
        }
    }

    function hideWarning() {
        var d = getDialog();
        if (d && d.open) {
            d.close();
        }
    }

    // Exposed globally so the template button can call it
    window.resetSessionTimer = function(pingServer) {
        clearTimeout(timer);
        clearTimeout(logoutTimer);
        hideWarning();
        timer = setTimeout(showWarning, WARN_AT);
        logoutTimer = setTimeout(function() {
            // POST-based logout via form submission
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '/my/logout/';
            var csrf = document.querySelector('meta[name="csrf-token"]');
            if (csrf) {
                var input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'csrfmiddlewaretoken';
                input.value = csrf.getAttribute('content');
                form.appendChild(input);
            }
            document.body.appendChild(form);
            form.submit();
        }, LOGOUT_AT);
        // Only ping server when explicitly requested (e.g. "I'm still here" button)
        if (pingServer) {
            fetch('/my/', { method: 'HEAD', credentials: 'same-origin' }).catch(function() {});
        }
    };

    // Prevent <dialog> Escape key from triggering quick-exit
    // (dialog natively closes on Escape — we intercept to reset timer instead)
    document.addEventListener('cancel', function(e) {
        var d = getDialog();
        if (d && d.open) {
            e.preventDefault();
            window.resetSessionTimer(true);
        }
    });

    // Reset timer on user activity (debounced to avoid excessive resets)
    var activityDebounce = null;
    function onActivity() {
        if (activityDebounce) return;
        activityDebounce = setTimeout(function() {
            activityDebounce = null;
        }, 5000);
        // Only reset if dialog is not showing
        var d = getDialog();
        if (!d || !d.open) {
            window.resetSessionTimer();
        }
    }

    ['mousemove', 'keypress', 'click', 'scroll', 'touchstart'].forEach(function(evt) {
        document.addEventListener(evt, onActivity, { passive: true });
    });

    // Start the timer
    window.resetSessionTimer();
})();
