Demand Transformation
====================

Overview
--------

Demand transformation is an optimization technique used in QueryBridge to improve query performance.
It works by generating additional predicates that help the XSB Datalog engine focus only on
the relevant data needed to answer a query, reducing unnecessary computation.

How It Works
-----------

1. **Analyzing Bound Arguments**: When a GraphQL query contains arguments, these can be used to
   restrict the search space. For example, in a query like ``user(id: "123") { name }``, we only need
   to consider the user with ID "123".

2. **Generating Demand Rules**: The system generates special "demand" predicates that represent
   which data is needed to answer the query.

3. **Magic Sets Transformation**: The technique applies a variation of the magic sets transformation
   to propagate the demand information through the query.

4. **Optimized Execution**: The XSB engine can then use these demand rules to restrict its search
   to only relevant data.

Example
-------

Consider this GraphQL query:

.. code-block:: graphql

   {
     user(id: "123") {
       name
       posts {
         title
       }
     }
   }

Without demand transformation, the system would retrieve all users and their posts, then filter.
With demand transformation, the system generates rules like:

.. code-block:: prolog

   % Seed demand with bound arguments for user
   demand_user_B("123").
   
   % Magic predicate for user
   m_user_B(ROOT) :- demand_user_B("123").
   
   % Propagate demand from user to its fields
   demand_posts_(USER_1) :- m_user_B(ROOT), user_ext(ROOT, USER_1).
   
   % Magic predicate for posts
   m_posts__(USER_1) :- demand_posts_(USER_1).

The resulting XSB query only considers the user with ID "123" and their posts.

Usage
-----

To enable demand transformation, pass ``True`` as the third argument to ``translate_graphql_to_xsb``:

.. code-block:: python

   from querybridge import translate_graphql_to_xsb
   
   # With demand transformation
   optimized_xsb = translate_graphql_to_xsb('schema.graphql', 'query.graphql', True)

Or with the command-line interface:

.. code-block:: bash

   python -m querybridge schema.graphql query.graphql --demand