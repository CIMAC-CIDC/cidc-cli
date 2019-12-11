"""Terms and Conditions for using the CIDC CLI."""

import click

from . import cache

# Copied verbatim from cli.interface.cli.CIDCCLI.info
TERMS = """
Welcome to the CIDC Command Line Interface (CLI) Tool.

You are about to access a system which contains data protected by federal law.

Unauthorized use of this system is strictly prohibited and subject to criminal
and civil penalties. All information stored on this system is owned by the
National Cancer Institute (NCI)."


By using this tool, you consent to the monitoring and recording of your
actions on this system. You also agree to refrain from engaging in any illegal
or improper behavior while using this system.

By downloading any data from the CIDC information system, you are agreeing to
take responsibility for the security of said data. You may not copy, transmit,
print out, or in any way cause the information to leave a secured computing
environment where it may be seen or accessed by unauthorized individuals.

Sharing your account with anyone else is strictly prohibited.

If you become aware of any threat to the system or possible breach of data,
you are required to immediately notify the CIDC.
"""

AGREEMENT = "Do you agree to the above terms and conditions?"

BOUNDARY = "=" * (len(AGREEMENT) + 10)

CONSENT_KEY = "consent"


def check_consent() -> bool:
    """Check that a user consents to the CLI user agreement."""
    # Has a user already consented?
    past_consent = cache.get(CONSENT_KEY)

    # If not, prompt the user to agree to the terms.
    if not past_consent:
        click.echo(TERMS)
        if click.confirm(AGREEMENT):
            # Store the user's response so we only need to ask them once.
            cache.store(CONSENT_KEY, "consented")
            click.echo("\nYour response has been stored.")
            click.echo(BOUNDARY)
        else:
            return False

    return True
