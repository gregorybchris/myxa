<div align="center">
  <img src="assets/myxa-banner.png">

  <h1>Myxa</h1>

  <p>
    <strong>Compatibility-aware package manager</strong>
  </p>

  <hr />
</div>

## About

Myxa has two goals:

1. Enable package maintainers to safely publish packages without breaks
2. Enable package users to easily upgrade to the latest versions of packages without breaks

### How it works

Along with package dependencies, Myxa also tracks the type signatures of each function in a package. When a breaking change is detected in a type signature, `myxa publish` will require a major version bump.

For large packages, most of the time breaking changes only affect a small proportion of users. If a user depends on feature X in their project, but only feature Y breaks, then `myxa update` will safely auto-upgrade, even across major version boundaries.

## Installation

Install using [uv](https://docs.astral.sh/uv)

```bash
uv sync
```

## Usage

First, set an environment variable to an index.json file, which will track your published packages locally.

```bash
export MYXA_INDEX="path/to/index.json"
```

Then just use Myxa like most modern package managers!

```bash
# Initialize a new package
mx init <name> "<description>"

# Show package info
mx info

# Show package info for a specific version
mx info --version <version>

# Add a package dependency
mx add <dep-name>

# Add a package dependency with a specific version
mx add <dep-name> --version <version>

# Remove a package dependency
mx remove <dep-name>

# Lock the package dependencies
mx lock

# Update all package dependencies to the highest compatible versions
mx update

# Check whether there are breaking changes
mx check

# Publish to the index
mx publish

# Show index info
mx index
```

### Unsupported features

- Integration with Python code
- Integration with PyPI
- Support for optional params
- Support for List, Dict, Tuple in functions
- Support for dev dependencies/groups/extras
- Support for upper bounds on dependencies
- Support for specifying preferred indexes in package metadata

## Package name

Myxa is named after the slime mold _Myxogastria_, the Ancient Greek word μύξα (_myxa_), meaning "mucus".
