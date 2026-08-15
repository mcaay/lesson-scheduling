# PROJECT CONTEXT

It's your responsibility to use all git commands, including git commit, git push and git pull.
This repo is not yet connected to github, but will be later.
The backups will be done on the hetzner side when the site goes to production, so you don't need to set it up.
The database should be in sqlite.
The project must be written in django framework.

# Project specific coding style

## Frontend
When asked to implement frontend elements, default to the way **Jason Fried** would implement it, the designer behind basecamp.com, hey.com and fizzy.do. The vibe of the website should be minimal, clean and professional, but with a human touch.

## Backend architecture
When asked to implement backend code or suggest the correct implementation architecture, default to the way **David Heinemeier Hansson**, also known as **DHH**, would implement it, the creator of Ruby on Rails, basecamp, hey and fizzy.

## General project conventions
- 4-space indentation in python, html, css and js.
- Use comments to explain intent and decisions.
- Use local helper imports (e.g., `core.my_algorithms`) instead of duplicating logic.
- Do not use class-based views.
- Keep template logic minimal; push computation into views.


# General coding guidelines

## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**
When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
