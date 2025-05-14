"""
QueryBridge: GraphQL to XSB Datalog Translator

A powerful tool for translating GraphQL queries into XSB Datalog,
with support for demand transformation optimization.
"""

from .translator import (
    SchemaType, 
    QueryField, 
    DemandInfo,
    parse_schema,
    parse_query,
    generate_xsb_for_query,
    translate_graphql_to_xsb
)

__version__ = "1.0.0"