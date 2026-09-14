# {{PROJECT_NAME}} project entrypoint

## Overview and scope

Describe what this project does, who maintains it, and what this entrypoint governs.

## Quick start

1. Read this file;
2. Read [`docs/README.md`](docs/README.md);
3. Follow the topic index that matches the current task;
4. Run the relevant commands below before declaring the stage complete.

## Context-loading order

~~~text
AGENTS.md
→ docs/README.md
→ relevant topic README.md
→ target document
→ supplementary documents linked by the target
~~~

## Key directories

| Path | Purpose |
| --- | --- |
| `{{SOURCE_DIRECTORY}}` | {{SOURCE_PURPOSE}} |
| `docs/` | Project knowledge and governance documents |
| `{{TEST_DIRECTORY}}` | {{TEST_PURPOSE}} |

## Common commands

~~~bash
{{INSTALL_COMMAND}}
{{CHECK_COMMAND}}
{{TEST_COMMAND}}
~~~

## Mandatory rules

- {{MANDATORY_RULE}}
- Keep documentation synchronized with code, configuration, interfaces, processes, deployment, and decisions;
- Record important constraints, pitfalls, and non-obvious decisions;
- Do not write secrets, tokens, passwords, or sensitive personal information.

## Prohibitions

- Do not modify business code when the task only asks for documentation governance;
- Do not overwrite or delete existing facts without checking conflicts and history;
- Do not declare a stage complete while its documentation gate is unsatisfied.

## Task routes

- Requirements and scope: [{{REQUIREMENTS_DOCUMENT}}]({{REQUIREMENTS_LINK}})
- Design and architecture: [{{DESIGN_DOCUMENT}}]({{DESIGN_LINK}})
- Testing and evidence: [{{TEST_DOCUMENT}}]({{TEST_LINK}})
- Release and deployment: [{{RELEASE_DOCUMENT}}]({{RELEASE_LINK}})

## Documentation index

Start with [`docs/README.md`](docs/README.md). Keep this file concise; put detailed knowledge in `docs/` and link it from the relevant index.
