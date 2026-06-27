import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_app_js(script):
    node = shutil.which("node")
    assert node is not None
    wrapped = f"""
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const __ROOT__ = {json.dumps(str(ROOT))};

const context = {{
    console: console,
    document: {{
        addEventListener: function () {{}}
    }},
    window: {{}}
}};

vm.createContext(context);
vm.runInContext(
    fs.readFileSync(path.join({json.dumps(str(ROOT))}, "scheduler/static/scheduler/app.js"), "utf8"),
    context
);

const ScheduleEditor = context.window.ScheduleEditor;

function assert(condition, message) {{
    if (!condition) {{
        throw new Error(message);
    }}
}}

function formFromFields(fields) {{
    return {{
        querySelectorAll: function (selector) {{
            const match = selector.match(/^\\[name="(.+)"\\]$/);
            const name = match ? match[1] : "";
            return (fields[name] || []).map(function (value) {{
                return {{value: value}};
            }});
        }}
    }};
}}

{script}
"""
    result = subprocess.run(
        [node, "-e", wrapped],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_editor_javascript_builds_spec_and_preserves_imported_raw_spec():
    run_app_js(
        """
assert(ScheduleEditor, "ScheduleEditor API is missing");

const form = formFromFields({
    lesson_block_days: ["Monday-Thursday", "Monday-Thursday", "Monday-Thursday"],
    lesson_block_start: ["18:00", "19:30", "21:00"],
    lesson_block_end: ["19:25", "20:55", "22:25"],
    room_name: ["Main Hall", "Small Studio"],
    room_capacity: ["30", "16"],
    instructor_name: ["Anna", "Ivona"],
    instructor_can_teach: ["Lindy Hop beginner, Solo Jazz beginner", "Lindy Hop beginner"],
    instructor_available: ["Monday-Thursday 17:00-22:30", "Monday-Thursday 17:00-22:30"],
    instructor_prefers_with: ["Ivona", "Anna"],
    group_name: ["Lindy Hop 1"],
    group_students: ["24"],
    group_style: ["Lindy Hop"],
    group_level: ["beginner"],
    group_lessons_per_week: ["1"],
    group_duration_minutes: ["85"],
    group_teachers: ["2"]
});

const generated = ScheduleEditor.buildSpec(form);
assert(generated.includes("room Small Studio"), "generated spec should include the second room");
assert(generated.includes("group Lindy Hop 1"), "generated spec should include the default group");

const generatedWithEmptyRows = ScheduleEditor.buildSpec(formFromFields({
    lesson_block_days: ["Monday"],
    lesson_block_start: ["18:00"],
    lesson_block_end: ["19:00"],
    room_name: ["Main Hall", ""],
    room_capacity: ["30", ""],
    instructor_name: ["Anna", ""],
    instructor_can_teach: ["Lindy Hop beginner", ""],
    instructor_available: ["Monday 17:00-22:00", ""],
    instructor_prefers_with: ["Ivona", ""],
    group_name: ["Lindy Hop 1", ""],
    group_students: ["24", ""],
    group_style: ["Lindy Hop", ""],
    group_level: ["beginner", ""],
    group_lessons_per_week: ["1", ""],
    group_duration_minutes: ["85", ""],
    group_teachers: ["2", ""]
}));
assert(
    generatedWithEmptyRows.indexOf("room \\n") === -1,
    "empty room rows should not be emitted"
);
assert(
    generatedWithEmptyRows.indexOf("instructor \\n") === -1,
    "empty instructor rows should not be emitted"
);
assert(
    generatedWithEmptyRows.indexOf("group \\n") === -1,
    "empty group rows should not be emitted"
);

let insertedHtml = "";
const added = ScheduleEditor.addRow("room", {
    querySelector: function (selector) {
        if (selector === "[data-room-template]") {
            return {innerHTML: "<div>new room</div>"};
        }
        if (selector === "[data-room-rows]") {
            return {
                insertAdjacentHTML: function (position, html) {
                    insertedHtml = position + ":" + html;
                }
            };
        }
        return null;
    }
});
assert(added === true, "addRow should report when a row was added");
assert(
    insertedHtml === "beforeend:<div>new room</div>",
    "addRow should append the template HTML to the row container"
);

const imported = "lesson blocks\\nFriday 18:00-19:25\\n\\nroom Imported Room\\ncapacity 10\\n";
assert(
    ScheduleEditor.shouldBuildSpec(generated, generated, false, false) === true,
    "matching default raw spec can be regenerated"
);
assert(
    ScheduleEditor.shouldBuildSpec(imported, generated, false, false) === false,
    "imported raw spec should be preserved when visible fields were not changed"
);
assert(
    ScheduleEditor.shouldBuildSpec(imported, generated, false, true) === true,
    "visible field edits should opt into rebuilding the spec"
);
assert(
    ScheduleEditor.shouldBuildSpec(imported, generated, true, true) === false,
    "manual raw spec edits should remain authoritative"
);
"""
    )


def test_editor_submit_handler_updates_raw_spec_only_when_it_should():
    run_app_js(
        """
const generated = ScheduleEditor.buildSpec(formFromFields({
    lesson_block_days: ["Monday-Thursday", "Monday-Thursday", "Monday-Thursday"],
    lesson_block_start: ["18:00", "19:30", "21:00"],
    lesson_block_end: ["19:25", "20:55", "22:25"],
    room_name: ["Main Hall", "Small Studio"],
    room_capacity: ["30", "16"],
    instructor_name: ["Anna", "Ivona"],
    instructor_can_teach: ["Lindy Hop beginner, Solo Jazz beginner", "Lindy Hop beginner"],
    instructor_available: ["Monday-Thursday 17:00-22:30", "Monday-Thursday 17:00-22:30"],
    instructor_prefers_with: ["Ivona", "Anna"],
    group_name: ["Lindy Hop 1"],
    group_students: ["24"],
    group_style: ["Lindy Hop"],
    group_level: ["beginner"],
    group_lessons_per_week: ["1"],
    group_duration_minutes: ["85"],
    group_teachers: ["2"]
}));

function makeElement(initialValue) {
    return {
        value: initialValue || "",
        listeners: {},
        addEventListener: function (eventName, callback) {
            this.listeners[eventName] = callback;
        },
        hasAttribute: function () {
            return true;
        },
        removeAttribute: function () {},
        setAttribute: function () {}
    };
}

function installWithRawSpec(rawText) {
    const elements = {
        lesson_block_days: [makeElement("Monday-Thursday"), makeElement("Monday-Thursday"), makeElement("Monday-Thursday")],
        lesson_block_start: [makeElement("18:00"), makeElement("19:30"), makeElement("21:00")],
        lesson_block_end: [makeElement("19:25"), makeElement("20:55"), makeElement("22:25")],
        room_name: [makeElement("Main Hall"), makeElement("Small Studio")],
        room_capacity: [makeElement("30"), makeElement("16")],
        instructor_name: [makeElement("Anna"), makeElement("Ivona")],
        instructor_can_teach: [makeElement("Lindy Hop beginner, Solo Jazz beginner"), makeElement("Lindy Hop beginner")],
        instructor_available: [makeElement("Monday-Thursday 17:00-22:30"), makeElement("Monday-Thursday 17:00-22:30")],
        instructor_prefers_with: [makeElement("Ivona"), makeElement("Anna")],
        group_name: [makeElement("Lindy Hop 1")],
        group_students: [makeElement("24")],
        group_style: [makeElement("Lindy Hop")],
        group_level: [makeElement("beginner")],
        group_lessons_per_week: [makeElement("1")],
        group_duration_minutes: [makeElement("85")],
        group_teachers: [makeElement("2")]
    };
    const rawSpec = makeElement(rawText);
    const toggle = makeElement("");
    const panel = makeElement("");
    const form = {
        listeners: {},
        addEventListener: function (eventName, callback) {
            this.listeners[eventName] = callback;
        },
        querySelectorAll: function (selector) {
            if (selector === "input, select, textarea") {
                return Object.values(elements).flat().concat([rawSpec]);
            }
            const match = selector.match(/^\\[name="(.+)"\\]$/);
            return match ? elements[match[1]] || [] : [];
        }
    };

    context.document.querySelector = function (selector) {
        if (selector === "[data-spec-form]") {
            return form;
        }
        if (selector === "[data-raw-spec-toggle]") {
            return toggle;
        }
        if (selector === "[data-raw-spec-panel]") {
            return panel;
        }
        if (selector === "[data-raw-spec-input]") {
            return rawSpec;
        }
        return null;
    };
    capturedDOMContentLoaded();
    return {form, rawSpec, elements};
}

let capturedDOMContentLoaded = null;
context.document.addEventListener = function (eventName, callback) {
    if (eventName === "DOMContentLoaded") {
        capturedDOMContentLoaded = callback;
    }
};
vm.runInContext(
    fs.readFileSync(path.join(__ROOT__, "scheduler/static/scheduler/app.js"), "utf8"),
    context
);

let installed = installWithRawSpec("lesson blocks\\nFriday 18:00-19:25\\n\\nroom Imported Room\\ncapacity 10\\n");
installed.form.listeners.submit();
assert(
    installed.rawSpec.value.includes("Imported Room"),
    "submit should preserve imported raw spec when visible fields did not change"
);

installed = installWithRawSpec(generated);
installed.elements.room_name[0].value = "Big Hall";
installed.elements.room_name[0].listeners.input();
installed.form.listeners.submit();
assert(
    installed.rawSpec.value.includes("room Big Hall"),
    "submit should rebuild raw spec after visible field edits"
);
"""
    )
