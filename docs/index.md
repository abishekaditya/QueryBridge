# QueryBridge Documentation

A Lean4 tool for translating GraphQL queries to XSB Datalog queries.

## Overview

QueryBridge is a library for translating GraphQL queries into XSB Datalog queries. This is useful for bridging graph-based query languages with logic-based systems, enabling semantic queries over graph data.

## Modules

- [QueryBridge](querybridge.md) - Main module
- [QueryBridge.Basic](querybridge_basic.md) - Core functionality for schema parsing and query translation
- [Main](main.md) - CLI interface

## Features

- Parse GraphQL schema files into structured representations
- Parse GraphQL query files into structured representations
- Generate equivalent XSB Datalog queries
- Simple and extensible design

## Usage

```lean
import QueryBridge

def main : IO Unit := do
  let result ← QueryBridge.translateGraphQLtoXSB "schema.graphql" "query.graphql"
  IO.println result
```

The above code will:
1. Parse the schema and query files
2. Translate the GraphQL query to XSB Datalog
3. Print the resulting XSB Datalog query