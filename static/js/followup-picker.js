/**
 * Follow-up Date Picker — progressive enhancement for date inputs.
 *
 * Replaces the bare native date input with quick-pick chips for common
 * follow-up intervals (Tomorrow, 3 days, Next week, 2 weeks) plus a
 * "Pick date" toggle for the native input as a fallback.
 *
 * The original <input type="date"> is kept and receives the value on
 * selection, so Django form processing is unchanged.
 *
 * Accessibility: WCAG 2.2 AA — radiogroup pattern with roving tabindex,
 * visible focus indicators, 44px touch targets.
 *
 * i18n: Uses Intl.DateTimeFormat with <html lang> for locale-aware dates.
 */
(function () {
    "use strict";

    // ---- Locale helpers ----
    var lang = document.documentElement.lang || "en";

    var dateFmt = new Intl.DateTimeFormat(lang, {
        month: "short", day: "numeric"
    });

    // Translated labels
    var labels = {
        en: {
            tomorrow: "Tomorrow",
            days: "{n} days",
            week: "1 week",
            weeks: "{n} weeks",
            pickDate: "Pick date",
            followUp: "Follow-up date"
        },
        fr: {
            tomorrow: "Demain",
            days: "{n} jours",
            week: "1 semaine",
            weeks: "{n} semaines",
            pickDate: "Choisir une date",
            followUp: "Date de suivi"
        }
    };
    var t = labels[lang] || labels.en;

    // ---- Quick-pick options (label, offset in days) ----
    var options = [
        { label: t.tomorrow, offset: 1 },
        { label: t.days.replace("{n}", "3"), offset: 3 },
        { label: t.week, offset: 7 },
        { label: t.weeks.replace("{n}", "2"), offset: 14 }
    ];

    // ---- Utilities ----
    function pad(n) { return n < 10 ? "0" + n : "" + n; }

    function toDateStr(d) {
        return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    }

    function addDays(date, days) {
        var result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    }

    function el(tag, attrs, children) {
        var node = document.createElement(tag);
        if (attrs) {
            for (var k in attrs) {
                if (k === "className") { node.className = attrs[k]; }
                else { node.setAttribute(k, attrs[k]); }
            }
        }
        if (children) {
            if (typeof children === "string") {
                node.textContent = children;
            } else if (Array.isArray(children)) {
                children.forEach(function (c) {
                    if (typeof c === "string") node.appendChild(document.createTextNode(c));
                    else if (c) node.appendChild(c);
                });
            } else {
                node.appendChild(children);
            }
        }
        return node;
    }

    // ---- Roving tabindex for radiogroup ----
    function setupRovingTabindex(container) {
        container.addEventListener("keydown", function (e) {
            var items = Array.prototype.slice.call(
                container.querySelectorAll("[role='radio']")
            );
            if (!items.length) return;
            var idx = items.indexOf(document.activeElement);
            if (idx < 0) return;

            var next = -1;
            if (e.key === "ArrowRight" || e.key === "ArrowDown") {
                next = (idx + 1) % items.length;
            } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
                next = (idx - 1 + items.length) % items.length;
            } else if (e.key === "Home") {
                next = 0;
            } else if (e.key === "End") {
                next = items.length - 1;
            }

            if (next >= 0) {
                e.preventDefault();
                items.forEach(function (it) { it.setAttribute("tabindex", "-1"); });
                items[next].setAttribute("tabindex", "0");
                items[next].focus();
            }
        });
    }

    // ---- Build the picker for one input ----
    function initFollowupPicker(input) {
        // Guard: don't initialise twice
        if (input.dataset.fpInitialised) return;
        input.dataset.fpInitialised = "true";

        var today = new Date();
        today.setHours(12, 0, 0, 0); // noon to avoid DST edge cases

        // Build chip container
        var chipContainer = el("div", {
            className: "mp-chips",
            role: "radiogroup",
            "aria-label": t.followUp
        });

        // Track state
        var selectedChip = null;
        var dateInput = input;
        var dateInputWrapper = el("div", { className: "fp-custom-date" });
        dateInputWrapper.style.display = "none";
        dateInputWrapper.style.marginTop = "var(--kn-space-sm, 8px)";
        dateInputWrapper.style.maxWidth = "220px";

        // Move input into wrapper
        var inputParent = dateInput.parentNode;
        inputParent.insertBefore(dateInputWrapper, dateInput);
        dateInputWrapper.appendChild(dateInput);

        // Quick-pick chips
        var chips = [];
        options.forEach(function (opt, i) {
            var targetDate = addDays(today, opt.offset);
            var dateStr = toDateStr(targetDate);
            var formattedDate = dateFmt.format(targetDate);

            var chip = el("button", {
                type: "button",
                className: "mp-chip",
                role: "radio",
                "aria-checked": "false",
                "data-date": dateStr,
                tabindex: i === 0 ? "0" : "-1"
            }, [
                opt.label,
                " ",
                el("span", { className: "mp-chip-sub" }, formattedDate)
            ]);

            chip.addEventListener("click", function () {
                if (selectedChip === chip) {
                    // Deselect (field is optional)
                    deselectAll();
                    dateInput.value = "";
                    triggerChange();
                } else {
                    selectChip(chip);
                    dateInput.value = dateStr;
                    dateInputWrapper.style.display = "none";
                    triggerChange();
                }
            });

            chips.push(chip);
            chipContainer.appendChild(chip);
        });

        // "Pick date" chip
        var pickDateChip = el("button", {
            type: "button",
            className: "mp-chip",
            role: "radio",
            "aria-checked": "false",
            tabindex: "-1"
        }, t.pickDate);

        pickDateChip.addEventListener("click", function () {
            deselectAll();
            dateInputWrapper.style.display = "block";
            dateInput.focus();
        });

        chips.push(pickDateChip);
        chipContainer.appendChild(pickDateChip);

        // Insert chips before the date input wrapper
        inputParent.insertBefore(chipContainer, dateInputWrapper);

        // Keyboard navigation
        setupRovingTabindex(chipContainer);

        // When native input changes, deselect quick-pick chips
        dateInput.addEventListener("change", function () {
            var val = dateInput.value;
            // Check if the value matches a quick-pick
            var matched = false;
            chips.forEach(function (chip) {
                if (chip.dataset.date && chip.dataset.date === val) {
                    selectChip(chip);
                    matched = true;
                }
            });
            if (!matched) {
                deselectAll();
                if (val) {
                    // Show "Pick date" as active state
                    pickDateChip.setAttribute("aria-checked", "true");
                    selectedChip = pickDateChip;
                }
            }
        });

        // Pre-populate: if input already has a value (edit mode)
        if (dateInput.value) {
            var matched = false;
            chips.forEach(function (chip) {
                if (chip.dataset.date && chip.dataset.date === dateInput.value) {
                    selectChip(chip);
                    matched = true;
                }
            });
            if (!matched) {
                // Custom date — show the input
                dateInputWrapper.style.display = "block";
                pickDateChip.setAttribute("aria-checked", "true");
                selectedChip = pickDateChip;
            }
        }

        // ---- Helpers ----
        function selectChip(chip) {
            deselectAll();
            chip.setAttribute("aria-checked", "true");
            chip.setAttribute("tabindex", "0");
            selectedChip = chip;
        }

        function deselectAll() {
            chips.forEach(function (c) {
                c.setAttribute("aria-checked", "false");
            });
            selectedChip = null;
            // Restore tabindex to first chip
            if (chips.length) chips[0].setAttribute("tabindex", "0");
        }

        function triggerChange() {
            // Dispatch change event so autosave picks it up
            var event;
            if (typeof Event === "function") {
                event = new Event("change", { bubbles: true });
            } else {
                event = document.createEvent("Event");
                event.initEvent("change", true, true);
            }
            dateInput.dispatchEvent(event);
        }
    }

    // ---- Initialise all follow-up pickers on the page ----
    function initAll() {
        var inputs = document.querySelectorAll(
            "input[type='date'][data-followup-picker]"
        );
        inputs.forEach(initFollowupPicker);
    }

    // Run on page load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }

    // Reinitialise after HTMX swaps (inline quick note form)
    document.body.addEventListener("htmx:afterSwap", function (event) {
        var target = event.detail.target;
        if (target) {
            var inputs = target.querySelectorAll(
                "input[type='date'][data-followup-picker]"
            );
            inputs.forEach(initFollowupPicker);
        }
    });
})();
