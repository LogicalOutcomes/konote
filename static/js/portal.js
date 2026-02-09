/**
 * Portal JavaScript — quick exit + session timeout warning.
 */

// Quick exit — immediately leave and destroy session
function quickExit() {
    // Best-effort session destruction via sendBeacon
    navigator.sendBeacon('/my/emergency-logout/');
    // Replace current history entry so back button doesn't return here
    window.location.replace('https://www.google.ca');
}

// Keyboard shortcut: Escape key triggers quick exit
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        quickExit();
    }
});

// Session timeout warning at 25 minutes (1500 seconds)
(function() {
    var WARN_AT = 25 * 60 * 1000;  // 25 minutes in ms
    var LOGOUT_AT = 30 * 60 * 1000;  // 30 minutes in ms
    var timer = null;
    var logoutTimer = null;

    function resetTimer() {
        clearTimeout(timer);
        clearTimeout(logoutTimer);
        hideWarning();
        timer = setTimeout(showWarning, WARN_AT);
        logoutTimer = setTimeout(function() {
            window.location.href = '/my/logout/';
        }, LOGOUT_AT);
    }

    function showWarning() {
        var dialog = document.getElementById('session-timeout-warning');
        if (dialog) {
            dialog.removeAttribute('hidden');
            dialog.setAttribute('role', 'alertdialog');
            dialog.setAttribute('aria-modal', 'true');
            // Focus the "I'm still here" button
            var btn = dialog.querySelector('[data-action="extend"]');
            if (btn) btn.focus();
        }
    }

    function hideWarning() {
        var dialog = document.getElementById('session-timeout-warning');
        if (dialog) {
            dialog.setAttribute('hidden', '');
        }
    }

    // "I'm still here" button handler
    document.addEventListener('click', function(e) {
        if (e.target && e.target.getAttribute('data-action') === 'extend') {
            resetTimer();
            // Ping server to reset session timeout
            fetch('/my/', { method: 'HEAD', credentials: 'same-origin' }).catch(function() {});
        }
    });

    // Reset timer on user activity
    ['mousemove', 'keypress', 'click', 'scroll', 'touchstart'].forEach(function(evt) {
        document.addEventListener(evt, resetTimer, { passive: true });
    });

    // Start the timer
    resetTimer();
})();
