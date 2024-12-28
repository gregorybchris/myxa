<div align="center">
  <h1>myxa</h1>

  <p>
    <strong>Compatibility aware package manager</strong>
  </p>

  <hr />
</div>

## Installation

Install using [uv](https://docs.astral.sh/uv)

```bash
uv sync
```

## Usage

```bash
# Initialize a new package
uv run mx init

# Show package info
uv run mx info --show-deps --show-modules

# Lock the package dependencies
uv run mx lock

# Add a package dependency
uv run mx add <dep-name>

# Remove a package dependency
uv run mx remove <dep-name>

# Publish to the index
uv run mx publish

# Update all package dependencies to the highest compatible versions
uv run mx update

# Show index info
uv run mx index --show-versions
```

## Package name

Myxa is named after the slime mold _Myxogastria_, the Ancient Greek word μύξα _myxa_, meaning "mucus".
