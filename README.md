# LSP-pyproject

This is a helper package that starts the [pyproject](https://github.com/terror/pyproject) language server for you.

## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) via Package Control.
2. Install [LSP-pyproject](https://packagecontrol.io/packages/LSP-pyproject) via Package Control.

## Applicable files

This language server operates on views with the `source.ini` base scope but only those that have `pyproject.toml` file name.

## Configuration

You can edit the global settings by opening the `Preferences: LSP-pyproject Settings` from the Command Palette.

Configure server-specific rules in your `pyproject.toml` under the `[tool.pyproject]` section.

Each rule can be set to a severity level (`error`, `warning`, `hint`, `information` (or `info`), or `off`) using either a simple string or a table with a `level` field:

```toml
[tool.pyproject.rules]
project-unknown-keys = "warning"
project-dependency-updates = { level = "hint" }
project-requires-python-upper-bound = "off"
```

Rule identifiers are shown in diagnostic output (e.g., `error[project-unknown-keys]`). Rules that aren't explicitly configured use their default severity level.
