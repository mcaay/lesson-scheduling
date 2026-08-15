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

    function pushField(lines, prefix, value) {
        if (value.trim()) {
            lines.push(prefix + value);
        }
    }

    function pushRepeatedField(lines, prefix, value) {
        value.split(/[,\n]/).forEach(function (part) {
            pushField(lines, prefix, part.trim());
        });
    }

    function pushPluralField(lines, prefix, value, singular, pluralText) {
        if (value.trim()) {
            lines.push(prefix + value + plural(value, singular, pluralText));
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
            if (hasAnyValue([days, start, end])) {
                pushLine(lines, days + " " + start + "-" + end);
            }
        });

        byName(form, "location_name").forEach(function (_, index) {
            var name = valueAt(form, "location_name", index);
            var roomsCount = valueAt(form, "location_rooms_count", index);
            if (!hasAnyValue([name, roomsCount])) {
                return;
            }
            lines.push("");
            pushLine(lines, "location " + name);
            pushField(lines, "rooms ", roomsCount);
        });

        byName(form, "instructor_name").forEach(function (_, index) {
            var name = valueAt(form, "instructor_name", index);
            var roles = valueAt(form, "instructor_roles", index);
            var minClasses = valueAt(form, "instructor_preferred_min_classes", index);
            var maxClasses = valueAt(form, "instructor_preferred_max_classes", index);
            var canTeach = valueAt(form, "instructor_can_teach", index);
            var available = valueAt(form, "instructor_available", index);
            var prefersWith = valueAt(form, "instructor_prefers_with", index);
            var avoidsWith = valueAt(form, "instructor_avoids_with", index);
            var cannotTeachWith = valueAt(form, "instructor_cannot_teach_with", index);
            var hasInstructorContent = hasAnyValue([
                name,
                roles,
                canTeach,
                available,
                prefersWith,
                avoidsWith,
                cannotTeachWith
            ]) || (minClasses && minClasses !== "1") || (maxClasses && maxClasses !== "3");
            if (!hasInstructorContent) {
                return;
            }
            lines.push("");
            pushLine(lines, "instructor " + name);
            pushField(lines, "roles ", roles);
            pushPluralField(lines, "prefers minimum ", minClasses, " class per week", " classes per week");
            pushPluralField(lines, "prefers maximum ", maxClasses, " class per week", " classes per week");
            pushField(lines, "can teach ", canTeach);
            pushRepeatedField(lines, "available ", available);
            pushField(lines, "prefers teaching with ", prefersWith);
            pushField(lines, "avoids teaching with ", avoidsWith);
            pushField(lines, "cannot teach with ", cannotTeachWith);
        });

        byName(form, "group_name").forEach(function (_, index) {
            var name = valueAt(form, "group_name", index);
            var lessons = valueAt(form, "group_lessons_per_week", index);
            var duration = valueAt(form, "group_duration_minutes", index);
            var teacherRoles = valueAt(form, "group_teacher_roles", index);
            var timeWindows = valueAt(form, "group_time_windows", index);
            if (!hasAnyValue([name, lessons, duration, teacherRoles, timeWindows])) {
                return;
            }
            lines.push("");
            pushLine(lines, "group " + name);
            pushPluralField(lines, "needs ", lessons, " lesson per week", " lessons per week");
            pushPluralField(lines, "duration ", duration, " minute", " minutes");
            pushField(lines, "teacher roles ", teacherRoles);
            pushRepeatedField(lines, "time window ", timeWindows);
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
        var documentScope = scope || document;
        var template = documentScope.querySelector("[data-" + kind + "-template]");
        var rows = documentScope.querySelector("[data-" + kind + "-rows]");

        if (!template || !rows) {
            return false;
        }

        rows.insertAdjacentHTML("beforeend", template.innerHTML);
        return true;
    }

    function removeRow(button) {
        var row = button.closest("[data-row]");
        if (!row) {
            return false;
        }
        row.remove();
        return true;
    }

    function setStatus(status, rawSpecDirty) {
        if (!status) {
            return;
        }
        status.textContent = rawSpecDirty
            ? "Raw spec edited manually. GUI changes will not overwrite it."
            : "Raw spec follows GUI changes.";
    }

    function installTabs(scope) {
        if (!scope.querySelectorAll) {
            return;
        }

        var tabButtons = Array.from(scope.querySelectorAll("[data-editor-tab]"));
        var panels = Array.from(scope.querySelectorAll("[data-tab-panel]"));

        function activateTab(name) {
            tabButtons.forEach(function (button) {
                var isActive = button.getAttribute("data-editor-tab") === name;
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-selected", isActive ? "true" : "false");
            });

            panels.forEach(function (panel) {
                var isActive = panel.getAttribute("data-tab-panel") === name;
                if (isActive) {
                    panel.removeAttribute("hidden");
                } else {
                    panel.setAttribute("hidden", "");
                }
            });
        }

        tabButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                activateTab(button.getAttribute("data-editor-tab"));
            });
        });
    }

    function installEditor(documentScope) {
        var scope = documentScope || document;
        var form = scope.querySelector("[data-spec-form]");
        var rawSpec = scope.querySelector("[data-raw-spec-input]");
        var status = scope.querySelector("[data-raw-spec-status]");
        var rawSpecDirty = false;
        var formDirty = false;

        if (!form || !rawSpec) {
            return;
        }

        installTabs(scope);

        function syncRawSpec() {
            if (!rawSpecDirty) {
                rawSpec.value = buildSpec(form);
            }
            setStatus(status, rawSpecDirty);
        }

        rawSpec.value = rawSpec.value.trim() ? rawSpec.value : buildSpec(form);
        var initialGeneratedSpec = buildSpec(form);
        setStatus(status, rawSpecDirty);

        rawSpec.addEventListener("input", function () {
            rawSpecDirty = true;
            setStatus(status, rawSpecDirty);
        });

        function handleGuiChange(event) {
            if (event.target === rawSpec) {
                return;
            }
            formDirty = true;
            syncRawSpec();
        }

        form.addEventListener("input", handleGuiChange);
        form.addEventListener("change", handleGuiChange);

        Array.from(form.querySelectorAll("input, select, textarea")).forEach(function (field) {
            if (field === rawSpec) {
                return;
            }
            field.addEventListener("input", function () {
                formDirty = true;
                syncRawSpec();
            });
            field.addEventListener("change", function () {
                formDirty = true;
                syncRawSpec();
            });
        });

        Array.from(form.querySelectorAll("[data-add-row]")).forEach(function (button) {
            button.addEventListener("click", function () {
                if (addRow(button.getAttribute("data-add-row"), form)) {
                    formDirty = true;
                    syncRawSpec();
                }
            });
        });

        form.addEventListener("click", function (event) {
            var button = null;
            if (event.target && event.target.matches && event.target.matches("[data-remove-row]")) {
                button = event.target;
            } else if (event.target && event.target.closest) {
                button = event.target.closest("[data-remove-row]");
            }
            if (!button) {
                return;
            }
            if (removeRow(button)) {
                formDirty = true;
                syncRawSpec();
            }
        });

        form.addEventListener("submit", function () {
            if (shouldBuildSpec(rawSpec.value, initialGeneratedSpec, rawSpecDirty, formDirty)) {
                rawSpec.value = buildSpec(form);
            }
        });
    }

    function installSolverLoading(documentScope) {
        var scope = documentScope || document;
        var loading = scope.querySelector("[data-solver-loading]");

        if (!loading || !scope.querySelectorAll) {
            return;
        }

        Array.from(scope.querySelectorAll("[data-solver-form]")).forEach(function (form) {
            form.addEventListener("submit", function (event) {
                var submitter = event.submitter;
                if (submitter && !submitter.hasAttribute("data-run-scheduler")) {
                    return;
                }

                loading.removeAttribute("hidden");
                if (submitter) {
                    submitter.disabled = true;
                }
                if (!root.fetch || !root.FormData) {
                    return;
                }

                event.preventDefault();
                root.fetch(form.action, {
                    method: "POST",
                    body: new root.FormData(form),
                    headers: {"X-Requested-With": "XMLHttpRequest"}
                })
                    .then(responseJson)
                    .then(function (data) {
                        pollSolveJob(data.status_url, loading, submitter);
                    })
                    .catch(function () {
                        restoreAfterSolveError(loading, submitter);
                    });
            });
        });
    }

    function pollSolveJob(statusUrl, loading, submitter) {
        root.fetch(statusUrl, {
            headers: {"X-Requested-With": "XMLHttpRequest"}
        })
            .then(responseJson)
            .then(function (data) {
                if (data.status === "pending") {
                    root.setTimeout(function () {
                        pollSolveJob(statusUrl, loading, submitter);
                    }, 1000);
                    return;
                }
                if (data.result_url) {
                    root.location.assign(data.result_url);
                    return;
                }
                restoreAfterSolveError(loading, submitter);
            })
            .catch(function () {
                restoreAfterSolveError(loading, submitter);
            });
    }

    function responseJson(response) {
        if (!response.ok) {
            throw new Error("Schedule request failed");
        }
        return response.json();
    }

    function restoreAfterSolveError(loading, submitter) {
        loading.setAttribute("hidden", "");
        if (submitter) {
            submitter.disabled = false;
        }
        if (root.alert) {
            root.alert("The scheduler could not be reached. Please try again.");
        }
    }

    root.ScheduleEditor = {
        addRow: addRow,
        buildSpec: buildSpec,
        installEditor: installEditor,
        installSolverLoading: installSolverLoading,
        removeRow: removeRow,
        shouldBuildSpec: shouldBuildSpec
    };

    if (typeof document !== "undefined") {
        document.addEventListener("DOMContentLoaded", function () {
            installEditor(document);
            installSolverLoading(document);
        });
    }
}(typeof window !== "undefined" ? window : globalThis));
