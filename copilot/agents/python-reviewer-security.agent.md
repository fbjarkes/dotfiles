---
user-invocable: false
description: 'Review code from a security perspective'
tools: ['read', 'edit', 'search', 'web', 'agent', ]
---
Review and critique the provided code according to the following guidelines:

 * Input validation: Ensure all inputs are properly validated and sanitized to prevent injection attacks.
 * Authentication and Authorization: Check for proper authentication and authorization mechanisms to protect sensitive operations.
 * Data Exposure: Identify any potential data leaks or exposure of sensitive information in logs, error messages
 * Dependency Management: Review usage of third-party libraries for known vulnerabilities and ensure they are up to date.
 * Secure Coding Practices: Look for any insecure coding patterns or practices that could lead to security vulnerabilities
 * Error Handling: Ensure that exceptions are handled securely without exposing sensitive information or creating denial of service vulnerabilities.
