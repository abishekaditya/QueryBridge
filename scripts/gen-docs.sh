#!/bin/bash

# Generate documentation using doc-gen4
set -e

PROJECT_DIR=$(pwd)
DOCS_DIR="${PROJECT_DIR}/docs"

echo "Preparing to generate documentation..."

# Ensure docs directory exists
mkdir -p "${DOCS_DIR}"

# Check if DocGen4 is correctly set up
if ! grep -q "DocGen4" lakefile.toml; then
  echo "DocGen4 is not set up in lakefile.toml. Adding it now..."
  cat >> lakefile.toml << EOF
# Documentation generation support
[dependencies]
DocGen4 = { git = "https://github.com/leanprover/doc-gen4", rev = "main" }

# Documentation configuration
[configuration]
[configuration.doc]
title = "QueryBridge Documentation"
description = "A tool for translating GraphQL queries to XSB Datalog"
EOF
fi

# Create the configuration file for doc-gen4
cat > doc-gen.toml << EOF
[doc-gen4]
rootModule = "QueryBridge"
srcDir = "src"
outDir = "docs"
styleSheet = "atom-one-light"
modulePrefix = "QueryBridge"
mainModuleTypes = [
  "def", "class", "structure", "inductive"
]
mainModuleDocs = true
EOF

# Get the latest dependencies including DocGen4
echo "Updating dependencies..."
lake update

# Build the project first to ensure everything is up-to-date
echo "Building the project..."
lake build

# Build doc-gen4 executable
echo "Building doc-gen4..."
cd .lake/packages/DocGen4
lake build

# Check for the doc-gen4 executable
DOC_GEN_PATH="./.lake/packages/DocGen4/.lake/build/bin/doc-gen4"
if [ ! -f "$DOC_GEN_PATH" ]; then
  echo "doc-gen4 not found at $DOC_GEN_PATH"
  echo "Trying alternate location..."
  DOC_GEN_PATH="./doc-gen4"
  if [ ! -f "$DOC_GEN_PATH" ]; then
    echo "Error: doc-gen4 executable not found. Documentation generation failed."
    exit 1
  fi
fi

# Return to project directory
cd "$PROJECT_DIR"

# Run doc-gen4 with the configuration
echo "Generating documentation using doc-gen4..."
"$DOC_GEN_PATH" --config doc-gen.toml

if [ -d "$DOCS_DIR" ] && [ "$(ls -A "$DOCS_DIR")" ]; then
  echo "Documentation successfully generated in ${DOCS_DIR}"
  echo "You can view the documentation by opening ${DOCS_DIR}/index.html in a web browser"
else
  echo "Error: Documentation not generated in ${DOCS_DIR}"
  exit 1
fi