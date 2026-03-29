"""Middleware layer for the Verdict API.

Provides cross-cutting concerns applied to every request:
- Rate limiting (token bucket algorithm)
- Request timing and correlation IDs
"""
