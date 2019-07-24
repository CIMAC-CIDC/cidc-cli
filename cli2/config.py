import os
from pathlib import Path

from . import cache

# General config
CIDC_WORKING_DIR = os.path.join(Path.home(), '.cidc')
TOKEN_CACHE_PATH = os.path.join(CIDC_WORKING_DIR, 'id_token')
UPLOAD_WORKSPACE = os.path.join(CIDC_WORKING_DIR, 'upload-workspace')


# Environment management
_ENV_KEY = 'env'


def set_env(value: str):
    """Set the current CLI environment"""
    cache.store(_ENV_KEY, value)


def get_env():
    """Get the current CLI environment"""
    return cache.get(_ENV_KEY) or 'prod'


# Environment-specific config
_current_env = get_env()
if _current_env == 'prod':
    API_V2_URL = 'https://api.cimac-network.org'
elif _current_env == 'staging':
    API_V2_URL = 'https://staging-api.cimac-network.org'
elif _current_env == 'dev':
    API_V2_URL = 'http://localhost:5000'
else:
    raise ValueError(f'Unsupported environment: {_current_env}')
