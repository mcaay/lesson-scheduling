(function (root) {
    function byName(form, name) {
        return Array.from(form.querySelectorAll('[name="' + name + '"]'));
    }

    function valueAt(form, name, index) {
        var field = byName(form, name)[index];
        return field ? field.value.trim() : "";
    }

    function pushLine(lines, line) {
        if (line.trim()) {
            lines.push(line);
        }
    }

    function plural(value, singular, pluralText) {
        return String(value) === "1" ? singular : pluralText;
    }

    function hasAnyValue(values) {
        return values.some(function (value) {
            return value !== "";
        });
    }

    function buildSpec(form) {
        var lines = ["lesson blocks"];
        var blockDays = byName(form, "lesson_block_days");

        blockDays.forEach(function (_, index) {
            var days = valueAt(form, "lesson_block_days", index);
            var start = valueAt(form, "lesson_block_start", index);
            var end = valueAt(form, "lesson_block_end", index);
            pushLine(lines, days + " " + start + "-" + end);
        });

        byName(form, "room_name").forEach(function (_, index) {
            var name = valueAt(form, "room_name", index);
            var capacity = valueAt(form, "room_capacity", index);
            if (!hasAnyValue([name, capacity])) {
                return;
            }
            lines.push("");
            pushLine(lines, "room " + name);
            pushLine(lines, "capacity " + capacity);
        });

        byName(form, "instructor_name").forEach(function (_, index) {
            var name = valueAt(form, "instructor_name", index);
            var canTeach = valueAt(form, "instructor_can_teach", index);
            var available = valueAt(form, "instructor_available", index);
            var prefersWith = valueAt(form, "instructor_prefers_with", index);
            if (!hasAnyValue([name, canTeach, available, prefersWith])) {
                return;
            }
            lines.push("");
            pushLine(lines, "instructor " + name);
            pushLine(lines, "can teach " + canTeach);
            pushLine(lines, "available " + available);
            pushLine(lines, "prefers teaching with " + prefersWith);
        });

        byName(form, "group_name").forEach(function (_, index) {
            var name = valueAt(form, "group_name", index);
            var students = valueAt(form, "group_students", index);
            var style = valueAt(form, "group_style", index);
            var level = valueAt(form, "group_level", index);
            var lessons = valueAt(form, "group_lessons_per_week", index);
            var duration = valueAt(form, "group_duration_minutes", index);
            var teachers = valueAt(form, "group_teachers", index);
            if (!hasAnyValue([name, students, style, level, lessons, duration, teachers])) {
                return;
            }
            lines.push("");
            pushLine(lines, "group " + name);
            pushLine(lines, "students " + students);
            pushLine(lines, "style " + style);
            pushLine(lines, "level " + level);
            pushLine(lines, "needs " + lessons + plural(lessons, " lesson per week", " lessons per week"));
            pushLine(lines, "duration " + duration + plural(duration, " minute", " minutes"));
            pushLine(lines, "teachers " + teachers);
        });

        return lines.join("\n") + "\n";
    }

    function normalizeSpec(text) {
        return text.replace(/\r\n/g, "\n").trim();
    }

    function shouldBuildSpec(rawSpecValue, generatedSpec, rawSpecDirty, formDirty) {
        if (rawSpecDirty) {
            return false;
        }
        if (formDirty) {
            return true;
        }
        return normalizeSpec(rawSpecValue) === normalizeSpec(generatedSpec);
    }

    function addRow(kind, scope) {
        var root = scope || document;
        var template = root.querySelector("[data-" + kind + "-template]");
        var rows = root.querySelector("[data-" + kind + "-rows]");

        if (!template || !rows) {
            return false;
        }

        rows.insertAdjacentHTML("beforeend", template.innerHTML);
        return true;
    }

    function installEditor() {
        var form = document.querySelector("[data-spec-form]");
        var toggle = document.querySelector("[data-raw-spec-toggle]");
        var panel = document.querySelector("[data-raw-spec-panel]");
        var rawSpec = document.querySelector("[data-raw-spec-input]");
        var rawSpecDirty = false;
        var formDirty = false;

        if (!form || !toggle || !panel || !rawSpec) {
            return;
        }

        var initialGeneratedSpec = buildSpec(form);

        toggle.addEventListener("click", function () {
            var isHidden = panel.hasAttribute("hidden");
            if (isHidden) {
                panel.removeAttribute("hidden");
                toggle.textContent = "Hide raw spec";
            } else {
                panel.setAttribute("hidden", "");
                toggle.textContent = "Show raw spec";
            }
        });

        rawSpec.addEventListener("input", function () {
            rawSpecDirty = true;
        });

        Array.from(form.querySelectorAll("input, select, textarea")).forEach(function (field) {
            if (field === rawSpec) {
                return;
            }
            field.addEventListener("input", function () {
                formDirty = true;
            });
            field.addEventListener("change", function () {
                formDirty = true;
            });
        });

        Array.from(form.querySelectorAll("[data-add-row]")).forEach(function (button) {
            button.addEventListener("click", function () {
                if (addRow(button.getAttribute("data-add-row"), form)) {
                    formDirty = true;
                }
            });
        });

        form.addEventListener("submit", function () {
            if (shouldBuildSpec(rawSpec.value, initialGeneratedSpec, rawSpecDirty, formDirty)) {
                rawSpec.value = buildSpec(form);
            }
        });
    }

    root.ScheduleEditor = {
        addRow: addRow,
        buildSpec: buildSpec,
        shouldBuildSpec: shouldBuildSpec
    };

    if (typeof document !== "undefined") {
        document.addEventListener("DOMContentLoaded", installEditor);
    }
}(typeof window !== "undefined" ? window : globalThis));
