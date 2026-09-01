"""Application security configuration."""

from apps.policies.policy import ApplicationFilePolicy
from security_system.system import System


# Create the security system with the application's filesystem policy
system = System(ApplicationFilePolicy())