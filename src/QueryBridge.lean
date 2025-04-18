import QueryBridge.Basic

/-!
# QueryBridge

A library for translating GraphQL queries to XSB Datalog.

## Features

* Parse GraphQL schema files into structured representations
* Parse GraphQL query files into structured representations
* Generate equivalent XSB Datalog queries
* Simple and extensible design

## Overview

The QueryBridge library provides tools to translate GraphQL queries into XSB Datalog
queries. This is useful for bridging graph-based query languages with logic-based
systems, enabling semantic queries over graph data.

## Main components

* `QueryBridge.Basic` - Core translation functionality

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
-/