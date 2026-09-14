# Project configuration

## Lookup order

Look for project configuration in this order and read the first valid file. If more than one exists, report the duplicate configuration and ask the user to choose; do not merge them silently:

~~~text
.r-doc.yaml
docs/r-doc.yaml
r-doc.yaml
~~~

When no configuration exists, use the default rules. Configuration can override project conventions, but it cannot disable sensitive-content protection, conflict reporting, non-destructive changes, or evidence requirements.

## Recommended shape

~~~yaml
version: 1
project_type: auto
docs_root: docs
required_document_types:
  - requirements
  - design
  - testing
exclude:
  - .git
  - node_modules
  - dist
  - build
gates:
  review: audit
  release: audit
relationships:
  require_for:
    requirements:
      - design
    design:
      - testing
~~~

Optional fields:

- `project_type`: `auto` or a project-type name; use it to override automatic detection;
- `docs_root`: the documentation root, defaulting to `docs`;
- `required_document_types`: document types explicitly required by the project;
- `exclude`: additional directory or file patterns to exclude;
- `gates`: stage strength such as `advisory`, `audit`, or `blocking`;
- `relationships.require_for`: minimum relationships between document types.

Report unknown fields and invalid configuration, then continue with default checks. Do not treat a configuration error as a passing audit.
