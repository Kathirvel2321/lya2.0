"""Retired insecure enrollment entry point.

The former command uploaded raw face and voice recordings to Supabase. LYA's
current enrollment contract is local-only and lives in security.registration.
This file remains as a fail-closed guard for old shortcuts and documentation.
"""

import sys


def enroll(*_args, **_kwargs):
    raise PermissionError(
        "Legacy cloud biometric enrollment is disabled. "
        "Use the reviewed local registration flow with trusted-device proof."
    )


if __name__ == "__main__":
    print(
        "LYA refused this legacy command: it could transmit raw face and voice data.\n"
        "The local admin-registration screen is not connected to real devices yet."
    )
    sys.exit(2)
