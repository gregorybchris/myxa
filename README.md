<div align="center">
  <h1>myxa</h1>

  <p>
    <strong>Compatibility aware package manager</strong>
  </p>

  <hr />
</div>

## About

> Note: myxa is just a toy project, not a full package manager. If you want this kind of behavior in your preferred package manager... me too :)

Myxa has two goals:

1. Enable package maintainers to safely publish packages without breaks
2. Enable package users to easily upgrade to the latest versions of packages without breaks

### How it works

Myxa tracks not only dependencies, but also the type signatures of each function in a package. When a breaking change is detected in a type signature, `myxa publish` will require a major version bump.

For large dependencies, most of the time a breaking change only affects a small proportion of users. If a user depends on feature X in their project, but only feature Y breaks, then `myxa update` will auto-upgrade across major version boundaries.

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
