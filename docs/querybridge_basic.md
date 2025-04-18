# QueryBridge.Basic

Core functionality for schema parsing and query translation.

## Functions and Types

/--
Represents a GraphQL schema type.

Examples:
- `scalar "String"` represents a scalar type like `String`
- `object "User" [("name", scalar "String")]` represents a type with fields
- `list (scalar "User")` represents a list type like `[User]`
- `nonNull (scalar "String")` represents a non-null type like `String!`
### Functions

```lean
inductive SchemaType where
structure QueryField where
def parseSchema (schemaPath : String) : IO (List SchemaType) := do
def containsChar (s : String) (c : Char) : Bool :=
def parseQuery (queryPath : String) : IO (List QueryField) := do
def capitalize (s : String) : String :=
def generateXsb (schema : List SchemaType) (query : List QueryField) : String :=
def translateGraphQLtoXSB (schemaPath : String) (queryPath : String) : IO String := do
```
