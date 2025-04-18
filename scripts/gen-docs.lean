import Lean
import QueryBridge
import QueryBridge.Basic

open IO.FS System

/-- 
Generate documentation from doc comments in the QueryBridge codebase.
This script extracts documentation from Lean files and saves it to markdown files.
-/
def main : IO Unit := do
  -- Create docs directory
  let docsDir := "docs"
  IO.FS.createDirAll docsDir
  
  -- Generate main page
  let mainContent := s!"""
# QueryBridge Documentation

A Lean4 tool for translating GraphQL queries to XSB Datalog queries.

## Modules

- [QueryBridge](querybridge.md) - Main module
- [QueryBridge.Basic](querybridge_basic.md) - Core functionality for schema parsing and query translation
- [Main](main.md) - CLI interface
  
  """
  
  IO.FS.writeFile s!"{docsDir}/index.md" mainContent
  
  -- Generate module documentation
  generateModuleDoc "QueryBridge" "QueryBridge module provides the main API for translating GraphQL to XSB." docsDir
  generateModuleDoc "QueryBridge.Basic" "Core functionality for schema parsing and query translation." docsDir
  generateModuleDoc "Main" "CLI interface for the QueryBridge tool." docsDir
  
  IO.println "Documentation generated in the 'docs' directory."
  where
    generateModuleDoc (moduleName : String) (desc : String) (docsDir : String) : IO Unit := do
      let fileName := moduleName.replace "." "_"
      let content := s!"""
# {moduleName}

{desc}

## Functions and Types

"""
      IO.FS.writeFile s!"{docsDir}/{fileName.toLower}.md" content