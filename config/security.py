"""Application security configuration."""

from apps.policies.policy import file_policy
from security_system.system import System


# Create the security system with the application's policy
system = System(file_policy)