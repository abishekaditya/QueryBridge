# QueryBridge.Basic Module

This module provides the core functionality for translating GraphQL queries into XSB Datalog queries.

## Data Structures

### SchemaType

```lean
inductive QueryBridge.SchemaType where
  | scalar (name : String) : SchemaType
  | object (name : String) (fields : List (String × SchemaType)) : SchemaType
  | list (elementType : SchemaType) : SchemaType
  | nonNull (innerType : SchemaType) : SchemaType
```

Represents a GraphQL schema type.

**Examples:**
- `scalar "String"` represents a scalar type like `String`
- `object "User" [("name", scalar "String")]` represents a type with fields
- `list (scalar "User")` represents a list type like `[User]`
- `nonNull (scalar "String")` represents a non-null type like `String!`

### QueryField

```lean
structure QueryBridge.QueryField where
  name : String
  arguments : List (String × String)
  subfields : List QueryField
```

Represents a GraphQL query field with its name, arguments, and subfields.

**Example:**
```graphql
{
  project(name: "GraphQL") {
    tagline
  }
}
```

Would be represented as:
```lean
{ name := "project", 
  arguments := [("name", "GraphQL")],
  subfields := [{ name := "tagline", arguments := [], subfields := [] }]
}
```

## Functions

### parseSchema

```lean
def QueryBridge.parseSchema (schemaPath : String) : IO (List SchemaType)
```

Parses a GraphQL schema file and returns a list of schema types.

**Parameters:**
- `schemaPath`: Path to the GraphQL schema file

**Returns:**
- A list of `SchemaType` representing the parsed schema

### parseQuery

```lean
def QueryBridge.parseQuery (queryPath : String) : IO (List QueryField)
```

Parses a GraphQL query file and returns a list of query fields.

**Parameters:**
- `queryPath`: Path to the GraphQL query file

**Returns:**
- A list of `QueryField` representing the parsed query

### capitalize

```lean
def QueryBridge.capitalize (s : String) : String
```

Capitalizes the first letter of a string.

**Parameters:**
- `s`: The string to capitalize

**Returns:**
- A new string with the first letter capitalized

### generateXsb

```lean
def QueryBridge.generateXsb (schema : List SchemaType) (query : List QueryField) : String
```

Generates XSB Datalog code from a GraphQL query.

**Parameters:**
- `schema`: The parsed GraphQL schema
- `query`: The parsed GraphQL query

**Returns:**
- XSB Datalog code as a string

### translateGraphQLtoXSB

```lean
def QueryBridge.translateGraphQLtoXSB (schemaPath : String) (queryPath : String) : IO String
```

Main function to translate GraphQL queries to XSB Datalog.

**Parameters:**
- `schemaPath`: Path to the GraphQL schema file
- `queryPath`: Path to the GraphQL query file

**Returns:**
- XSB Datalog code as a string