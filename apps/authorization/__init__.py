"""
Application-level authorization package.

This package implements a lightweight ABAC-style PDP/PEP foundation.
It defines the policy vocabulary and makes authorization decisions.
"""

from .engine import authorize
from .types import AuthorizationRequest, Decision, Principal, RequestContext, Resource

__all__ = [
    "AuthorizationRequest",
    "Decision",
    "Principal",
    "RequestContext",
    "Resource",
    "authorize",
]