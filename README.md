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
mx init

# Show package info
mx info --show-deps --show-modules

# Lock the package dependencies
mx lock

# Add a package dependency
mx add <dep-name>

# Remove a package dependency
mx remove <dep-name>

# Publish to the index
mx publish

# Update all package dependencies to the highest compatible versions
mx update

# Show index info
mx index --show-versions
```

## Package name

Myxa is named after the slime mold _Myxogastria_, the Ancient Greek word μύξα _myxa_, meaning "mucus".
