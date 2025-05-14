# Demand Transformation in QueryBridge

This document explains how demand transformation is implemented in the QueryBridge project and how it optimizes GraphQL to Datalog translation.

## Introduction

Demand transformation (also known as magic-set transformation) is a key optimization technique used in deductive databases and query processing. It transforms a set of rules to make bottom-up evaluation more efficient by focusing computation only on relevant data.

## Why Use Demand Transformation?

Without demand transformation, Datalog engines often compute complete relation extensions, even when only a subset of the results is needed. This can be highly inefficient, especially for:

1. Queries with selective filters
2. Deeply nested hierarchical data
3. Large datasets where full scanning would be expensive
4. Recursive queries that could potentially explore large parts of a graph

## How Demand Transformation Works

The basic idea behind demand transformation is to:

1. Create special "demand" and "magic" predicates that identify which data is needed
2. Restrict rule evaluation based on these predicates
3. Propagate demand from query inputs down to all relevant subqueries

### Key Components

In our implementation, demand transformation involves several key components:

#### 1. Bound Arguments Identification

We first identify "bound" arguments in the query - these are constants or literals specified in the query, such as:

```graphql
{
  user(id: "1234") {  # "id: 1234" is a bound argument
    name
  }
}
```

Bound arguments create a starting point for demand propagation.

#### 2. Adornment Patterns

For each predicate, we create an "adornment pattern" indicating which arguments are bound (B) or free (F). For example:

- `demand_user_B` - indicates that the first argument to `user` is bound
- `demand_posts_BBF` - indicates that the first two arguments to `posts` are bound, but the third is free

#### 3. Demand Predicates

For each predicate and adornment pattern, we create a demand predicate:

```prolog
% Create demand for user with ID "1234"
demand_user_B("1234").
```

#### 4. Magic Predicates

Magic predicates serve as guards for rule evaluation, ensuring that only relevant tuples are computed:

```prolog
% Magic predicate definition
m_user_B(UserID) :- demand_user_B(UserID).

% Guarded rule
user_result(UserID, Name, Email) :- m_user_B(UserID), user_ext(UserID, Name, Email).
```

#### 5. Demand Propagation

Demand is propagated to related entities through join relationships:

```prolog
% Propagate demand from users to their posts
demand_posts_B(UserID) :- m_user_B(UserID).
m_posts_B(PostID) :- demand_posts_B(UserID), user_posts_ext(UserID, PostID).
```

## Example: Filter Arguments

Consider this GraphQL query with filter arguments:

```graphql
{
  users(minAge: 25, maxAge: 40, nameContains: "Smith") {
    name
    email
  }
}
```

Without demand transformation, we would need to:
1. Process ALL users
2. Filter to those between 25-40 years old
3. Filter to those with "Smith" in their name

With demand transformation, the resulting Datalog code includes:

```prolog
% Seed demand with filter values
demand_users_BBB(25, 40, "Smith").

% Magic predicate to guard computation
m_users_BBB(ROOT) :- demand_users_BBB(25, 40, "Smith").

% Query with guard that passes in filter values
users_result(ID, Name, Age, Email) :-
  m_users_BBB(ROOT),  % Demand guard
  user(ID, Name, Age, Email, _),
  Age >= 25,  % Connected to demand through variables
  Age =< 40,  % Connected to demand through variables
  contains(Name, "Smith").  % Connected to demand through variables
```

This approach allows the Datalog engine to:
1. Start with the specific filter values (25, 40, "Smith")
2. Use these values to drive data retrieval
3. Only process users that match the filter criteria

## Example: Nested Relationships

For a nested query like:

```graphql
{
  user(id: "1") {
    name
    posts {
      title
      comments {
        text
      }
    }
  }
}
```

Demand transformation creates a chain:

```prolog
% Seed initial demand
demand_user_B("1").

% Define magic predicates
m_user_B(UserID) :- demand_user_B(UserID).

% Propagate demand to posts
demand_posts_B(UserID) :- m_user_B(UserID).
m_posts_B(PostID) :- demand_posts_B(UserID), user_posts(UserID, PostID).

% Propagate demand to comments
demand_comments_B(PostID) :- m_posts_B(PostID).
m_comments_B(CommentID) :- demand_comments_B(PostID), post_comments(PostID, CommentID).

% Guarded rules for data access
user_result(UserID, UserName) :- m_user_B(UserID), user_ext(UserID, UserName).
post_result(PostID, Title) :- m_posts_B(PostID), post_ext(PostID, Title).
comment_result(CommentID, Text) :- m_comments_B(CommentID), comment_ext(CommentID, Text).
```

This ensures that:
1. We only process the specific user with ID "1"
2. We only process posts belonging to that user
3. We only process comments belonging to those posts

## Implementation Details

In the QueryBridge Python implementation, demand transformation is implemented in several key functions:

1. `generate_demand_transformation()` - Creates demand and magic predicates for a field
2. `generate_xsb_for_query()` - Applies demand transformation to queries 

The implementation includes detailed comments indicating where demand transformation has been applied and why.

## Benchmarking and Performance

Demand transformation generally provides the most benefit in these scenarios:

1. **High selectivity filters** - When filters are highly selective (matching few records)
2. **Deep nesting** - When queries involve multiple levels of nested relationships
3. **Large datasets** - When the underlying data size is large
4. **Complex recursive queries** - When queries would otherwise explore large portions of a graph

In our testing, we've observed that demand transformation can provide orders of magnitude performance improvements in these scenarios.

## References

1. Bancilhon, F., Maier, D., Sagiv, Y., & Ullman, J. D. (1986). "Magic sets and other strange ways to implement logic programs." In *Proceedings of the 5th ACM Symposium on Principles of Database Systems* (PODS '86), pp. 1-15.

2. Beeri, C., & Ramakrishnan, R. (1991). "On the power of magic." *Journal of Logic Programming*, 10(3-4), pp. 255-299.

3. Tekle, K.T., & Liu, Y.A. (2010). "More efficient datalog queries: subsumptive tabling beats magic sets." In *Proceedings of the 2010 ACM SIGMOD International Conference on Management of Data*, pp. 661-672.

4. Liu, Y., & Stoller, S. D. (2009). "From Datalog Rules to Efficient Programs with Precise Complexity Analysis." *ACM Transactions on Programming Languages and Systems* (TOPLAS), 31(6), pp. 1-38.
EOF < /dev/null