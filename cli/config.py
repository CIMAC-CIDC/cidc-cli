import os
from time import sleep
from pathlib import Path
import click

from . import cache

# General config
CIDC_WORKING_DIR = os.path.join(Path.home(), ".cidc")
TOKEN_CACHE_PATH = os.path.join(CIDC_WORKING_DIR, "id_token")


# Environment management
_ENV_KEY = "env"


def set_env(value: str):
    """Set the current CLI environment"""
    cache.store(_ENV_KEY, value)


def get_env():
    """Get the current CLI environment"""
    return cache.get(_ENV_KEY) or "prod"


_WARNING = "\n".join(
    [
        "##      ##    ###    ########  ##    ## #### ##    ##  ######   ",
        "##  ##  ##   ## ##   ##     ## ###   ##  ##  ###   ## ##    ##  ",
        "##  ##  ##  ##   ##  ##     ## ####  ##  ##  ####  ## ##        ",
        "##  ##  ## ##     ## ########  ## ## ##  ##  ## ## ## ##   #### ",
        "##  ##  ## ######### ##   ##   ##  ####  ##  ##  #### ##    ##  ",
        "##  ##  ## ##     ## ##    ##  ##   ###  ##  ##   ### ##    ##  ",
        " ###  ###  ##     ## ##     ## ##    ## #### ##    ##  ######   ",
        "",
    ]
)
_STRIKE = "*" * 64


def check_env_warning(ignore_env):
    """Get the current CLI environment"""
    if get_env() != "prod":
        print(_STRIKE + "\n" + _WARNING + _STRIKE)
        print(f"You are using DEVELOPMENT environment ({get_env()})")
        if ignore_env != None and ignore_env == get_env():
            return

        print("If you are not sure what that means, stop now.\n" + _STRIKE)

        if not click.confirm("Proceed anyways?"):
            if click.confirm(
                "Do you want to reset the CLI to its default configuration?"
            ):
                set_env("prod")
                print(_STRIKE)
                print("Environment set to default, you can retry now.")
            exit(0)

        print(_STRIKE)

    if ignore_env != None and ignore_env != get_env():
        print(_STRIKE + "\n" + _WARNING + _STRIKE)
        print(f"You are using PRODUCTION environment, not {ignore_env}")
        print(f"Remove `--ignore {ignore_env}` and retry.")
        print(_STRIKE)
        exit(0)


# Environment-specific config
_current_env = get_env()
if _current_env == "prod":
    API_V2_URL = "https://api.cimac-network.org"
elif _current_env == "staging":
    API_V2_URL = "https://staging-api.cimac-network.org"
elif _current_env == "dev":
    API_V2_URL = "http://localhost:8000"
else:
    raise ValueError(f"Unsupported environment: {_current_env}")
