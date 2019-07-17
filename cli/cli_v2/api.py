"""Implements a client for the CIDC API running on Google App Engine"""
from typing import Optional

import requests

from ..constants import API_V2_URL


class ApiError(Exception):
    pass


def _url(endpoint: str):
    endpoint = endpoint.lstrip("/")
    return f"{API_V2_URL}/{endpoint}"


def auth_header(id_token: str):
    return {'Authorization': f'Bearer {id_token}'}


def check_auth(id_token: str) -> Optional[str]:
    """Check if an id_token is valid by making a request to the base API URL."""
    response = requests.get(API_V2_URL, headers=auth_header(id_token))

    # 401 Unauthorized, so token is invalid
    if response.status_code == 401:
        data = response.json()
        return data['_error']['message']

    # We got some other, unexpected HTTP error
    if response.status_code != 200:
        raise ApiError(
            f"Auth check resulted in an unexpected error: Status Code {response.status_code}")

    # No errors, so the token is valid
    return None
