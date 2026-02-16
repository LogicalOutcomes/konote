/**
 * Meeting Picker — progressive enhancement for datetime-local inputs.
 *
 * Replaces the browser's clunky native datetime-local picker with:
 *   - Date quick-pick chips (Today, Tomorrow) + weekday row + date fallback
 *   - Time slot grid (business hours, 30-min increments)
 *   - Live summary of the selected date & time
 *
 * The original <input type="datetime-local"> is kept hidden and receives
 * the combined value on selection, so Django form processing is unchanged.
 *
 * Accessibility: WCAG 2.2 AA — radiogroup pattern with roving tabindex,
 * visible focus indicators, aria-live summary.
 *
 * i18n: Uses Intl.DateTimeFormat with the page's <html lang> for automatic
 * locale-aware date/time formatting (EN/FR).
 */
(function () {
    "use strict";

    // ---- Configuration (read from data attributes, fall back to defaults) ----
    var configEl = document.getElementById("meeting-time-config");
    var MIN_HOUR = configEl ? parseInt(configEl.getAttribute("data-time-start"), 10) || 9 : 9;
    var MAX_HOUR_RAW = configEl ? parseInt(configEl.getAttribute("data-time-end"), 10) || 17 : 17;
    var STEP_MINUTES = configEl ? parseInt(configEl.getAttribute("data-time-step"), 10) || 30 : 30;
    // MAX_HOUR is the last hour that gets slots — e.g. end=17 means last slot at 16:30 (with 30-min step)
    var MAX_HOUR = MAX_HOUR_RAW - 1;
    var WEEKDAYS_TO_SHOW = 5; // Mon-Fri

    // ---- Locale helpers ----
    var lang = document.documentElement.lang || "en";

    var dateFmtShort = new Intl.DateTimeFormat(lang, {
        weekday: "short", month: "short", day: "numeric"
    });
    var dateFmtFull = new Intl.DateTimeFormat(lang, {
        weekday: "long", year: "numeric", month: "long", day: "numeric"
    });
    var dateFmtWeekday = new Intl.DateTimeFormat(lang, { weekday: "short" });
    var dateFmtDay = new Intl.DateTimeFormat(lang, { day: "numeric" });
    var timeFmt = new Intl.DateTimeFormat(lang, {
        hour: "numeric", minute: "2-digit", hour12: true
    });
    var timeFmt24 = new Intl.DateTimeFormat(lang, {
        hour: "2-digit", minute: "2-digit", hour12: false
    });

    // Translated labels — fallback to English
    var labels = {
        en: {
            location: "Location",
            inPerson: "In person",
            phone: "Phone",
            customLocation: "Other location",
            date: "Date",
            today: "Today",
            tomorrow: "Tomorrow",
            otherDate: "Other date:",
            time: "Time",
            chooseDate: "Choose a date",
            chooseTime: "Choose a time",
            selected: "Selected:",
            selectDateFirst: "Choose a date and time above",
            selectTimeNext: "Now choose a time"
        },
        fr: {
            location: "Lieu",
            inPerson: "En personne",
            phone: "T\u00e9l\u00e9phone",
            customLocation: "Autre lieu",
            date: "Date",
            today: "Aujourd\u2019hui",
            tomorrow: "Demain",
            otherDate: "Autre date\u00a0:",
            time: "Heure",
            chooseDate: "Choisir une date",
            chooseTime: "Choisir une heure",
            selected: "S\u00e9lectionn\u00e9\u00a0:",
            selectDateFirst: "Choisissez une date et une heure ci-dessus",
            selectTimeNext: "Maintenant, choisissez une heure"
        }
    };
    var t = labels[lang] || labels.en;

    // ---- Utilities ----
    function pad(n) { return n < 10 ? "0" + n : "" + n; }

    function toDateStr(d) {
        return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    }

    function isSameDate(a, b) {
        return a.getFullYear() === b.getFullYear() &&
               a.getMonth() === b.getMonth() &&
               a.getDate() === b.getDate();
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

    // ---- Roving tabindex helper ----
    // Within a radiogroup, arrow keys move focus; Tab leaves the group.
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

    // ---- Build the picker ----
    function init() {
        var hiddenInput = document.querySelector(
            "input[type='datetime-local'][name='start_timestamp']"
        );
        if (!hiddenInput) return; // Not a meeting form

        // Hide the native input + its label + the old calendar button + help text
        var formGroup = hiddenInput.closest("form");
        var oldLabel = formGroup.querySelector("label[for='" + hiddenInput.id + "']");
        var oldButton = document.getElementById("open-datetime-picker");
        var oldHelp = document.getElementById("meeting-start-help");
        var oldRequired = document.getElementById("meeting-start-required");

        hiddenInput.classList.add("mp-hidden");
        hiddenInput.setAttribute("tabindex", "-1");
        hiddenInput.removeAttribute("aria-describedby");
        if (oldLabel) oldLabel.classList.add("mp-hidden");
        if (oldButton) oldButton.classList.add("mp-hidden");
        if (oldHelp) oldHelp.classList.add("mp-hidden");
        if (oldRequired) oldRequired.classList.add("mp-hidden");

        // State
        var state = { date: null, time: null };

        // ---- Build the picker container ----
        var picker = el("div", { className: "mp-picker", id: "meeting-picker" });

        // Insert picker before the hidden input
        hiddenInput.parentNode.insertBefore(picker, hiddenInput);

        // ---- DATE SECTION ----
        var dateSection = el("div", { className: "mp-section" });
        dateSection.appendChild(el("span", {
            className: "mp-section-label", id: "mp-date-label"
        }, t.date));

        var today = new Date();
        today.setHours(0, 0, 0, 0);
        var tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        // Quick picks
        var dateGroup = el("div", {
            className: "mp-chips",
            role: "radiogroup",
            "aria-labelledby": "mp-date-label"
        });

        function makeQuickPick(label, subText, dateVal, ariaLabel) {
            var chip = el("button", {
                type: "button",
                className: "mp-chip",
                role: "radio",
                "aria-checked": "false",
                "aria-label": ariaLabel,
                "data-date": toDateStr(dateVal),
                tabindex: "-1"
            }, [
                label + " ",
                el("span", { className: "mp-chip-sub" }, subText)
            ]);
            return chip;
        }

        var todayChip = makeQuickPick(
            t.today,
            dateFmtShort.format(today),
            today,
            t.today + " " + dateFmtFull.format(today)
        );
        todayChip.setAttribute("tabindex", "0"); // first item gets tabindex 0
        dateGroup.appendChild(todayChip);

        dateGroup.appendChild(makeQuickPick(
            t.tomorrow,
            dateFmtShort.format(tomorrow),
            tomorrow,
            t.tomorrow + " " + dateFmtFull.format(tomorrow)
        ));

        dateSection.appendChild(dateGroup);

        // Weekday row — show the next 5 weekdays (skip today/tomorrow if already shown)
        var weekdayGroup = el("div", {
            className: "mp-weekdays",
            role: "radiogroup",
            "aria-labelledby": "mp-date-label"
        });

        var shownDates = [toDateStr(today), toDateStr(tomorrow)];
        var cursor = new Date(today);
        var weekdaysAdded = 0;

        // Advance to find weekdays not already shown as quick-picks
        for (var i = 0; i < 14 && weekdaysAdded < WEEKDAYS_TO_SHOW; i++) {
            cursor.setDate(cursor.getDate() + 1);
            var dow = cursor.getDay();
            if (dow === 0 || dow === 6) continue; // skip weekends
            var ds = toDateStr(cursor);
            if (shownDates.indexOf(ds) >= 0) continue; // skip today/tomorrow

            var wd = new Date(cursor);
            var wdBtn = el("button", {
                type: "button",
                className: "mp-weekday",
                role: "radio",
                "aria-checked": "false",
                "aria-label": dateFmtFull.format(wd),
                "data-date": toDateStr(wd),
                tabindex: "-1"
            }, [
                el("span", { className: "mp-weekday-name" }, dateFmtWeekday.format(wd)),
                el("span", { className: "mp-weekday-date" }, dateFmtDay.format(wd))
            ]);
            weekdayGroup.appendChild(wdBtn);
            weekdaysAdded++;
        }

        dateSection.appendChild(weekdayGroup);

        // "Other date" fallback
        var otherDateRow = el("div", { className: "mp-other-date" });
        var otherDateLabel = el("label", { "for": "mp-other-date-input" }, t.otherDate);
        var otherDateInput = el("input", {
            type: "date",
            id: "mp-other-date-input",
            "aria-label": t.otherDate
        });
        otherDateRow.appendChild(otherDateLabel);
        otherDateRow.appendChild(otherDateInput);
        dateSection.appendChild(otherDateRow);

        picker.appendChild(dateSection);

        // ---- TIME SECTION ----
        picker.appendChild(el("hr", { className: "mp-divider" }));

        var timeSection = el("div", { className: "mp-section" });
        timeSection.appendChild(el("span", {
            className: "mp-section-label", id: "mp-time-label"
        }, t.time));

        var timeGrid = el("div", {
            className: "mp-time-grid",
            role: "radiogroup",
            "aria-labelledby": "mp-time-label"
        });

        // Generate 30-min slots from MIN_HOUR to MAX_HOUR:30
        var firstTimeSlot = true;
        for (var h = MIN_HOUR; h <= MAX_HOUR; h++) {
            for (var m = 0; m < 60; m += STEP_MINUTES) {
                var slotDate = new Date(2000, 0, 1, h, m);
                var timeStr = pad(h) + ":" + pad(m);
                var displayTime = timeFmt.format(slotDate);
                var slot = el("button", {
                    type: "button",
                    className: "mp-time-slot",
                    role: "radio",
                    "aria-checked": "false",
                    "aria-label": displayTime,
                    "data-time": timeStr,
                    tabindex: firstTimeSlot ? "0" : "-1"
                }, displayTime);
                timeGrid.appendChild(slot);
                firstTimeSlot = false;
            }
        }

        timeSection.appendChild(timeGrid);
        picker.appendChild(timeSection);

        // ---- SUMMARY (live region) ----
        picker.appendChild(el("hr", { className: "mp-divider" }));

        var summary = el("div", {
            className: "mp-summary",
            "aria-live": "polite",
            "aria-atomic": "true",
            id: "mp-summary"
        }, t.selectDateFirst);
        picker.appendChild(summary);

        // ---- Setup roving tabindex on all radiogroups ----
        setupRovingTabindex(dateGroup);
        setupRovingTabindex(weekdayGroup);
        setupRovingTabindex(timeGrid);

        // ---- Event handlers ----

        function clearDateSelection() {
            var allDateBtns = picker.querySelectorAll("[data-date][role='radio']");
            allDateBtns.forEach(function (btn) {
                btn.setAttribute("aria-checked", "false");
            });
            otherDateInput.value = "";
        }

        function clearTimeSelection() {
            var allTimeBtns = timeGrid.querySelectorAll("[role='radio']");
            allTimeBtns.forEach(function (btn) {
                btn.setAttribute("aria-checked", "false");
            });
        }

        function filterTimeSlotsForToday() {
            // If selected date is today, hide past time slots
            var now = new Date();
            var isToday = state.date && isSameDate(new Date(state.date + "T00:00:00"), now);
            var slots = timeGrid.querySelectorAll("[data-time]");

            slots.forEach(function (slot) {
                if (isToday) {
                    var parts = slot.getAttribute("data-time").split(":");
                    var slotH = parseInt(parts[0], 10);
                    var slotM = parseInt(parts[1], 10);
                    if (slotH < now.getHours() ||
                        (slotH === now.getHours() && slotM <= now.getMinutes())) {
                        slot.style.display = "none";
                        // If this was selected, deselect it
                        if (slot.getAttribute("aria-checked") === "true") {
                            slot.setAttribute("aria-checked", "false");
                            state.time = null;
                        }
                    } else {
                        slot.style.display = "";
                    }
                } else {
                    slot.style.display = "";
                }
            });
        }

        function updateSummary() {
            if (!state.date && !state.time) {
                summary.textContent = t.selectDateFirst;
                return;
            }
            if (state.date && !state.time) {
                var d = new Date(state.date + "T12:00:00");
                summary.textContent = t.selected + " " + dateFmtFull.format(d) +
                    " \u2014 " + t.selectTimeNext;
                return;
            }
            if (state.date && state.time) {
                var dt = new Date(state.date + "T" + state.time + ":00");
                summary.textContent = t.selected + " " + dateFmtFull.format(dt) +
                    " " + timeFmt.format(dt);
            }
        }

        function syncHiddenInput() {
            if (state.date && state.time) {
                hiddenInput.value = state.date + "T" + state.time;
                // Fire change event for any listeners
                hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));
            } else {
                hiddenInput.value = "";
            }
            updateSummary();
        }

        // Date chip/weekday clicks
        function handleDateClick(e) {
            var btn = e.target.closest("[data-date]");
            if (!btn) return;
            e.preventDefault();
            clearDateSelection();
            btn.setAttribute("aria-checked", "true");
            state.date = btn.getAttribute("data-date");
            filterTimeSlotsForToday();
            syncHiddenInput();
        }

        dateGroup.addEventListener("click", handleDateClick);
        weekdayGroup.addEventListener("click", handleDateClick);

        // Also allow Space/Enter on radiogroup items
        function handleDateKey(e) {
            if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                var btn = e.target.closest("[data-date]");
                if (btn) {
                    clearDateSelection();
                    btn.setAttribute("aria-checked", "true");
                    state.date = btn.getAttribute("data-date");
                    filterTimeSlotsForToday();
                    syncHiddenInput();
                }
            }
        }
        dateGroup.addEventListener("keydown", handleDateKey);
        weekdayGroup.addEventListener("keydown", handleDateKey);

        // "Other date" input
        otherDateInput.addEventListener("change", function () {
            if (otherDateInput.value) {
                clearDateSelection();
                state.date = otherDateInput.value;
                filterTimeSlotsForToday();
                syncHiddenInput();
            }
        });

        // Time slot clicks
        timeGrid.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-time]");
            if (!btn || btn.style.display === "none") return;
            e.preventDefault();
            clearTimeSelection();
            btn.setAttribute("aria-checked", "true");
            state.time = btn.getAttribute("data-time");
            syncHiddenInput();
        });

        timeGrid.addEventListener("keydown", function (e) {
            if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                var btn = e.target.closest("[data-time]");
                if (btn && btn.style.display !== "none") {
                    clearTimeSelection();
                    btn.setAttribute("aria-checked", "true");
                    state.time = btn.getAttribute("data-time");
                    syncHiddenInput();
                }
            }
        });

        // ---- Pre-populate from existing value (edit mode) ----
        if (hiddenInput.value) {
            var parts = hiddenInput.value.split("T");
            if (parts.length === 2) {
                state.date = parts[0];
                state.time = parts[1].substring(0, 5); // HH:MM

                // Try to check matching date button
                var matchBtn = picker.querySelector(
                    "[data-date='" + state.date + "']"
                );
                if (matchBtn) {
                    matchBtn.setAttribute("aria-checked", "true");
                } else {
                    otherDateInput.value = state.date;
                }

                // Try to check matching time slot
                var matchTime = timeGrid.querySelector(
                    "[data-time='" + state.time + "']"
                );
                if (matchTime) {
                    matchTime.setAttribute("aria-checked", "true");
                }

                filterTimeSlotsForToday();
                updateSummary();
            }
        }
    }

    // Run on DOMContentLoaded
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
