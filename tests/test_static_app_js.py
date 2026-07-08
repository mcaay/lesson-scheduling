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

function element(value) {{
    return {{
        value: value || "",
        textContent: "",
        listeners: {{}},
        addEventListener: function (eventName, callback) {{
            this.listeners[eventName] = callback;
        }},
        hasAttribute: function (name) {{
            return !!this[name];
        }},
        removeAttribute: function (name) {{
            this[name] = false;
        }},
        setAttribute: function (name) {{
            this[name] = true;
        }}
    }};
}}

function formFromFields(fields) {{
    return {{
        querySelectorAll: function (selector) {{
            if (selector === "input, select, textarea") {{
                return Object.values(fields).flat();
            }}
            const match = selector.match(/^\\[name="(.+)"\\]$/);
            const name = match ? match[1] : "";
            return fields[name] || [];
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


def test_editor_javascript_builds_role_aware_spec_without_group_style_or_level():
    run_app_js(
        """
const form = formFromFields({
    lesson_block_days: [element("Monday-Thursday"), element("Monday-Thursday")],
    lesson_block_start: [element("18:00"), element("19:30")],
    lesson_block_end: [element("19:25"), element("20:55")],
    location_name: [element("Main Hall"), element("Small Studio")],
    location_rooms_count: [element("2"), element("1")],
    instructor_name: [element("Anna"), element("Ivona")],
    instructor_roles: [element("leader"), element("follower")],
    instructor_preferred_min_classes: [element("1"), element("1")],
    instructor_preferred_max_classes: [element("3"), element("3")],
    instructor_can_teach: [element("Lindy Hop beginner"), element("Lindy Hop beginner")],
    instructor_available: [element("Monday-Thursday 17:00-22:30"), element("Monday-Thursday 17:00-22:30")],
    instructor_prefers_with: [element("Ivona"), element("Anna")],
    instructor_avoids_with: [element(""), element("")],
    instructor_cannot_teach_with: [element("Ana"), element("")],
    group_name: [element("Lindy Hop beginner #1")],
    group_lessons_per_week: [element("1")],
    group_duration_minutes: [element("85")],
    group_teacher_roles: [element("leader, follower")]
});

const generated = ScheduleEditor.buildSpec(form);

assert(generated.includes("Monday-Thursday 18:00-19:25"), "lesson block should be emitted");
assert(generated.includes("location Small Studio"), "second location should be emitted");
assert(generated.includes("rooms 2"), "location room count should be emitted");
assert(!generated.includes("\\ncapacity "), "room capacity must not be emitted");
assert(!generated.includes("\\nstudents "), "student count must not be emitted");
assert(generated.includes("roles leader"), "leader role should be emitted");
assert(generated.includes("roles follower"), "follower role should be emitted");
assert(generated.includes("prefers minimum 1 class per week"), "minimum class preference should be emitted");
assert(generated.includes("prefers maximum 3 classes per week"), "maximum class preference should be emitted");
assert(generated.includes("cannot teach with Ana"), "hard pair constraints should be emitted");
assert(generated.includes("group Lindy Hop beginner #1"), "group name should carry course information");
assert(generated.includes("teacher roles leader, follower"), "group teacher roles should be emitted");
assert(!generated.includes("\\nstyle "), "group style must not be emitted");
assert(!generated.includes("\\nlevel "), "group level must not be emitted");
assert(!generated.includes("\\nteachers "), "teacher count must not be emitted");
"""
    )


def test_editor_javascript_supports_lesson_block_add_and_empty_row_skipping():
    run_app_js(
        """
let insertedHtml = "";
const added = ScheduleEditor.addRow("lesson-block", {
    querySelector: function (selector) {
        if (selector === "[data-lesson-block-template]") {
            return {innerHTML: "<div>new block</div>"};
        }
        if (selector === "[data-lesson-block-rows]") {
            return {
                insertAdjacentHTML: function (position, html) {
                    insertedHtml = position + ":" + html;
                }
            };
        }
        return null;
    }
});
assert(added === true, "lesson block rows should be addable");
assert(insertedHtml === "beforeend:<div>new block</div>", "lesson block template should append");

const generated = ScheduleEditor.buildSpec(formFromFields({
    lesson_block_days: [element("Monday"), element("")],
    lesson_block_start: [element("18:00"), element("")],
    lesson_block_end: [element("19:00"), element("")],
    location_name: [element("Main Hall"), element("")],
    location_rooms_count: [element("1"), element("")],
    instructor_name: [element("Anna"), element("")],
    instructor_roles: [element("leader"), element("")],
    instructor_preferred_min_classes: [element("1"), element("")],
    instructor_preferred_max_classes: [element("3"), element("")],
    instructor_can_teach: [element("Lindy Hop beginner"), element("")],
    instructor_available: [element("Monday 17:00-22:00"), element("")],
    instructor_prefers_with: [element(""), element("")],
    instructor_avoids_with: [element(""), element("")],
    instructor_cannot_teach_with: [element(""), element("")],
    group_name: [element("Lindy Hop beginner #1"), element("")],
    group_lessons_per_week: [element("1"), element("")],
    group_duration_minutes: [element("85"), element("")],
    group_teacher_roles: [element("leader"), element("")]
}));
assert(!generated.includes("location \\n"), "empty location rows should not be emitted");
assert(!generated.includes("instructor \\n"), "empty instructor rows should not be emitted");
assert(!generated.includes("prefers teaching with\\n"), "empty preference lines should not be emitted");
assert(!generated.includes("avoids teaching with\\n"), "empty avoid lines should not be emitted");
assert(!generated.includes("cannot teach with\\n"), "empty hard constraint lines should not be emitted");
assert(!generated.includes("group \\n"), "empty group rows should not be emitted");
"""
    )


def test_editor_javascript_live_syncs_gui_changes_until_raw_spec_is_edited():
    run_app_js(
        """
const fields = {
    lesson_block_days: [element("Monday")],
    lesson_block_start: [element("18:00")],
    lesson_block_end: [element("19:00")],
    location_name: [element("Main Hall")],
    location_rooms_count: [element("1")],
    instructor_name: [element("Anna")],
    instructor_roles: [element("leader")],
    instructor_preferred_min_classes: [element("1")],
    instructor_preferred_max_classes: [element("3")],
    instructor_can_teach: [element("Lindy Hop beginner")],
    instructor_available: [element("Monday 17:00-22:00")],
    instructor_prefers_with: [element("")],
    instructor_avoids_with: [element("")],
    instructor_cannot_teach_with: [element("")],
    group_name: [element("Lindy Hop beginner #1")],
    group_lessons_per_week: [element("1")],
    group_duration_minutes: [element("60")],
    group_teacher_roles: [element("leader")]
};
const rawSpec = element("");
const rawStatus = element("");
const toggle = element("");
const panel = element("");
const form = formFromFields(fields);
form.listeners = {};
form.addEventListener = function (eventName, callback) {
    this.listeners[eventName] = callback;
};
form.querySelectorAll = function (selector) {
    if (selector === "input, select, textarea") {
        return Object.values(fields).flat().concat([rawSpec]);
    }
    if (selector === "[data-add-row]") {
        return [];
    }
    const match = selector.match(/^\\[name="(.+)"\\]$/);
    return match ? fields[match[1]] || [] : [];
};
const fakeDocument = {
    querySelector: function (selector) {
        if (selector === "[data-spec-form]") return form;
        if (selector === "[data-raw-spec-toggle]") return toggle;
        if (selector === "[data-raw-spec-panel]") return panel;
        if (selector === "[data-raw-spec-input]") return rawSpec;
        if (selector === "[data-raw-spec-status]") return rawStatus;
        return null;
    }
};

ScheduleEditor.installEditor(fakeDocument);
assert(rawSpec.value.includes("location Main Hall"), "initial raw spec should be generated from GUI");

fields.location_name[0].value = "Big Hall";
fields.location_name[0].listeners.input({target: fields.location_name[0]});
assert(rawSpec.value.includes("location Big Hall"), "GUI edits should immediately update raw spec");

rawSpec.value = "manual spec";
rawSpec.listeners.input({target: rawSpec});
fields.location_name[0].value = "Small Hall";
fields.location_name[0].listeners.input({target: fields.location_name[0]});
assert(rawSpec.value === "manual spec", "manual raw spec edits should be authoritative");
assert(rawStatus.textContent.includes("Raw spec edited manually"), "manual mode should be visible");
"""
    )
