# QueryBridge: GraphQL‑to‑Datalog Optimizer

*Translate GraphQL queries into Datalog programs with demand transformation optimization.*

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
* Comprehensive documentation with Sphinx
* Automated testing for different query types
* Performance benchmarking tools
* Simple and extensible design

## Installation

1. Clone or download the repository:
```bash
git clone https://github.com/abishekaditya/QueryBridge
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

Report.pdf contains the report for the project.

cse505_presentation.pdf contains the presentation slides.

Comprehensive documentation is available in the `docs/` directory. The documentation is built with Sphinx and includes:

- API reference with auto-generated module documentation
- Detailed explanation of demand transformation optimization
- Usage examples and code snippets
- Getting started guide

To build the documentation:

```bash
cd docs
make html
```

Then open `docs/_build/html/index.html` in your browser.

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

## Testing and Benchmarking

### Testing

The project includes multiple test cases to verify functionality:

```bash
# Run basic tests
python test_basic.py

# Run nested query tests
python test_nested.py

# Run all tests
python tests.py

# Clean up generated files after testing
python cleanup.py
```

### Benchmarking

Performance benchmarking is available to measure translation speed and optimization impact:

```bash
# Run benchmarks
python benchmark.py

# Run benchmarks with specific options
python benchmark.py --iterations 100 --demand
```

## Project Structure

```
.
├── docs/                     # Documentation files
│   ├── _build/               # Built documentation output
│   ├── api/                  # API documentation
│   ├── source/               # Sphinx source files
│   ├── conf.py               # Sphinx configuration
│   ├── index.rst             # Documentation main page
│   ├── modules.rst           # Module documentation
│   ├── demand_transformation.rst # Demand transformation docs
│   ├── demand_optimization_example.md
│   └── querybridge_basic.md
├── src/                      # Source code
│   └── querybridge/          # Main package
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # CLI entry point
│       ├── Basic.lean        # Lean theorem prover integration
│       └── translator.py     # Core translator functionality
├── tests/                    # Test cases
│   ├── basic/                # Basic test for verification
│   │   ├── schema.graphql
│   │   ├── query.graphql
│   │   └── facts.P
│   └── nested/               # Nested query tests
│       ├── schema.graphql
│       ├── query.graphql
│       └── facts.P
├── benchmark.py              # Performance benchmark script
├── cleanup.py                # Cleanup script for generated files
├── test_basic.py             # Test runner for basic queries
├── test_nested.py            # Test runner for nested queries
├── tests.py                  # General test runner
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Prof. Yanhong Annie Liu](https://www3.cs.stonybrook.edu/~liu/) (Stony Brook University) for project guidance
- GraphQL Foundation for [graphql-core](https://github.com/graphql-python/graphql-core) library
- ([Claude AI](https://www.anthropic.com/claude)) for helping with documentation