# QueryBridge: GraphQL‑to‑Datalog Optimizer

*Translate GraphQL queries into provably optimal Datalog programs with demand transformation optimization.*

---

## Overview

QueryBridge is a tool that translates GraphQL queries into XSB Datalog, enabling semantic queries over graph data with optimal execution performance. It parses GraphQL schema and query files and generates equivalent XSB Datalog code.

A key feature is the demand transformation (magic sets) functionality, which optimizes queries by pushing filters down and reducing intermediate results. This can dramatically improve query performance for complex nested queries or queries with selective filters.

## Features

* Parse GraphQL schema files into structured representations
* Parse GraphQL query files into structured representations
* Generate equivalent XSB Datalog queries
* Apply demand transformation for query optimization
* Support for complex nested queries
* Simple and extensible design

## Installation

1. Clone or download the repository:
```bash
git clone <repository-url>
cd QueryBridge
```

2. Create a virtual environment and install the package:
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -e .
```

## Usage

### Command-line Interface

```bash
# Activate the virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run with default test files
python -m querybridge

# Run with custom files
python -m querybridge path/to/schema.graphql path/to/query.graphql --output path/to/output.xsb

# Run with demand transformation
python -m querybridge path/to/schema.graphql path/to/query.graphql --demand
```

### As a Library

```python
from querybridge import translate_graphql_to_xsb

# Without demand transformation
result = translate_graphql_to_xsb("schema.graphql", "query.graphql")
print(result)

# With demand transformation
optimized_result = translate_graphql_to_xsb("schema.graphql", "query.graphql", apply_demand=True)
print(optimized_result)
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- `docs/demand_optimization_example.md` - Explanation of demand transformation optimization
- `docs/index.md` - Overview of the library

## Examples

### Basic Query Translation

**GraphQL Schema:**
```graphql
type User {
  username: String!
}

type Project {
  name: String!
  tagline: String
  contributors: [User!]!
}

type Query {
  project(name: String!): Project
}
```

**GraphQL Query:**
```graphql
{
  project(name: "GraphQL") {
    tagline
  }
}
```

**Generated XSB Datalog:**
```prolog
ans(Tagline) :- project("GraphQL", Tagline).
```

### With Demand Transformation

When using demand transformation, the query optimizer generates additional rules to push filters down and reduce intermediate results:

```prolog
% Demand transformation facts and rules
% Seed demand with bound arguments for project
demand_project_B("GraphQL").

% Magic predicate for project
m_project_B(ROOT) :- demand_project_B("GraphQL").

% Query field rules
% Rules for field: project
project_result(ROOT, Tagline) :- m_project_B(ROOT), project_ext(ROOT, Tagline).

% Final answer predicate combining all query results
ans(Tagline) :- project_result(ROOT, Tagline).

% Demand transformation summary
% NOTE: Applied demand transformation 'demand_project_B' (B) because it has 1 bound argument(s)
```

## Testing

To run the test suite:

```bash
# Run the simple test
python test/simple/test_simple.py

# Run all tests (when available)
./run-tests.py

# Run specific tests
./run-tests.py basic nested_tables

# Keep output files for inspection
./run-tests.py --keep-output

# Run benchmarks to compare performance
./benchmark.py --iterations 5
```

## Project Structure

```
.
├── docs/                 # Documentation files
│   ├── demand_optimization_example.md
│   ├── demand_transformation.md
│   └── index.md
├── src/                  # Source code
│   └── querybridge/      # Main package
│       ├── __init__.py   # Package initialization
│       ├── __main__.py   # CLI entry point
│       └── translator.py # Core translator functionality
├── test/                 # Test cases
│   └── simple/            # Simple test for verification
│       ├── schema.graphql
│       ├── query.graphql
│       ├── facts.P
│       └── test_simple.py
├── benchmark.py          # Performance benchmark script
├── query_bridge.py       # Standalone script version
├── run-tests.py          # Test runner script
├── setup.py              # Package installation script
└── README.md             # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Prof. Yanhong Annie Liu (Stony Brook University) for project guidance
- GraphQL Foundation for graphql-core library