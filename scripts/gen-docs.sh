#!/bin/bash

# Generate simple documentation for QueryBridge
set -e

PROJECT_DIR=$(pwd)
DOCS_DIR="${PROJECT_DIR}/docs"

echo "Preparing to generate documentation..."

# Ensure docs directory exists
mkdir -p "${DOCS_DIR}"

# Create doc-gen.toml (even if we won't use it with doc-gen4)
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

# Build the project first to ensure everything is up-to-date
echo "Building the project..."
lake build

# Generate documentation structure manually
echo "Generating basic documentation structure..."

# Create the main index file
cat > "${DOCS_DIR}/index.md" << EOF
# QueryBridge Documentation

A Lean4 tool for translating GraphQL queries to XSB Datalog queries.

## Modules

- [QueryBridge](querybridge.md) - Main module
- [QueryBridge.Basic](querybridge_basic.md) - Core functionality for schema parsing and query translation
- [Main](main.md) - CLI interface
EOF

# Create module documentation files with basic structure
create_module_doc() {
  local module_name="$1"
  local description="$2"
  local file_name=$(echo "$module_name" | tr '.' '_' | tr '[:upper:]' '[:lower:]')
  
  cat > "${DOCS_DIR}/${file_name}.md" << EOF
# ${module_name}

${description}

## Functions and Types

EOF

  # Try to append some code documentation if we can find it
  echo "Extracting documentation for ${module_name}..."
  
  if [ "$module_name" == "QueryBridge" ]; then
    source_file="${PROJECT_DIR}/src/QueryBridge.lean"
  elif [ "$module_name" == "QueryBridge.Basic" ]; then
    source_file="${PROJECT_DIR}/src/QueryBridge/Basic.lean"
  elif [ "$module_name" == "Main" ]; then
    source_file="${PROJECT_DIR}/src/Main.lean"
  else
    source_file=""
  fi
  
  if [ -n "$source_file" ] && [ -f "$source_file" ]; then
    # Extract docstrings (lines that start with /-- and end with -/)
    grep -A 20 "/--" "$source_file" | while read -r line; do
      if [[ "$line" == *"-/"* ]]; then
        break
      fi
      echo "$line" >> "${DOCS_DIR}/${file_name}.md"
    done
    
    # Extract function declarations
    echo "### Functions" >> "${DOCS_DIR}/${file_name}.md"
    echo "" >> "${DOCS_DIR}/${file_name}.md"
    echo '```lean' >> "${DOCS_DIR}/${file_name}.md"
    grep -E "^def |^inductive |^structure " "$source_file" >> "${DOCS_DIR}/${file_name}.md"
    echo '```' >> "${DOCS_DIR}/${file_name}.md"
  fi
}

# Create module documentation
create_module_doc "QueryBridge" "QueryBridge module provides the main API for translating GraphQL to XSB."
create_module_doc "QueryBridge.Basic" "Core functionality for schema parsing and query translation."
create_module_doc "Main" "CLI interface for the QueryBridge tool."

echo "Documentation successfully generated in ${DOCS_DIR}"
echo "You can view the documentation by opening ${DOCS_DIR}/index.md in a web browser"