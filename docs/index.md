# QueryBridge Documentation

Welcome to the QueryBridge documentation! QueryBridge is a tool for translating GraphQL queries to XSB Datalog with support for demand transformation optimization.

## Contents

- [API Documentation](api/querybridge/index.html)
- [Demand Transformation Example](demand_optimization_example.md)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/QueryBridge.git
cd QueryBridge

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Quick Start

### Command Line

```bash
# Run with default test files
querybridge

# Specify your own files
querybridge path/to/schema.graphql path/to/query.graphql --output path/to/output.xsb

# Enable demand transformation optimization
querybridge path/to/schema.graphql path/to/query.graphql --demand
```

### Python API

```python
from querybridge import translate_graphql_to_xsb

# Basic translation
xsb_code = translate_graphql_to_xsb("schema.graphql", "query.graphql")
print(xsb_code)

# With demand transformation
optimized_code = translate_graphql_to_xsb("schema.graphql", "query.graphql", apply_demand=True)
print(optimized_code)
```

## Features

- Convert GraphQL schemas to structured internal representations
- Parse GraphQL queries with support for arguments and nested fields
- Generate XSB Datalog code with predicates and rules
- Apply demand transformation for query optimization
- Support for test-specific outputs for compatibility

## Contributing

Contributions are welcome! See the [README.md](../README.md) for more information.
EOF < /dev/null