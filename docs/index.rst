.. QueryBridge documentation master file, created by
   sphinx-quickstart on Wed May 14 18:47:57 2025.

QueryBridge Documentation
=========================

QueryBridge is a powerful tool for translating GraphQL queries into XSB Datalog, with
support for demand transformation optimization.

Features
--------

* Parse GraphQL schemas and queries
* Translate GraphQL queries to XSB Datalog
* Apply demand transformation for optimization
* Command-line interface for easy integration

Getting Started
--------------

Installation
^^^^^^^^^^^

.. code-block:: bash

   pip install querybridge

Basic Usage
^^^^^^^^^^

.. code-block:: python

   from querybridge import translate_graphql_to_xsb
   
   # Translate a GraphQL query to XSB Datalog
   xsb_code = translate_graphql_to_xsb('schema.graphql', 'query.graphql')
   print(xsb_code)
   
   # Apply demand transformation for optimization
   optimized_xsb = translate_graphql_to_xsb('schema.graphql', 'query.graphql', True)

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   modules
   demand_transformation

