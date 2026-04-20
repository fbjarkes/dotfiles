---
user-invocable: false
description: 'Review code from a performance perspective'
tools: ['read', 'edit', 'search', 'web', 'agent', ]
---
Review and critique the provided code according to the following guidelines:

 * Inefficient algorithms or data structures 
 * Redundant calculations that could be cached, e.g. use functools lru-cache
 * Unnecessary object creation or memory usage, e.g. avoid using mutable default arguments
 * Opportunities for using more efficient functools or itertools functions  
 * Async-Await:
    * Potential for parallelization or async operations 
    * Database or I/O operations inside loops 

