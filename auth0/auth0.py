#!/usr/bin/env python3
"""
Module that handles authentication with auth0
"""

import urllib
import re
import webbrowser
import hashlib
import secrets
import socket
import time
from typing import Tuple
from base64 import urlsafe_b64encode
import requests


CRYPTOPAIR = Tuple[bytes, str]
DOMAIN = "https://cidc-test.auth0.com/authorize?"
AUDIENCE = 'http://localhost:5000'
CLIENT_ID = 'w0PxQ5deugPZSnP0kWbtXyw5olaEAOMy'
CODE_CHALLENGE_METHOD = 'S256'
REDIRECT_URI = 'http://localhost:5001/get_code'
SCOPE = 'openid profile email'


def base_64_urlencode(random_bytes: bytes) -> bytes:
    """
    Encodes bytes to a URL safe b64 encoded sequence.

    Arguments:
        random_bytes {bytes} -- Byte array.

    Returns:
        bytes -- Base 64 encoded bites.
    """
    return urlsafe_b64encode(random_bytes)


def sha256(buffer: bytes) -> bytes:
    """
    Hashes a series of b64 encoded bits using sha256.

    Arguments:
        buffer {bytes} -- Base 64 encoded bytes.

    Returns:
        bytes -- Hashed bytes.
    """
    obj_hash = hashlib.sha256()
    obj_hash.update(buffer)
    return obj_hash.digest()


def create_crypto_pair() -> CRYPTOPAIR:
    """
    Creates a crpytographically random string to prevent MIM attacks.

    Returns:
        Tuple -- Verifier (bytes), Challenge_str (string)
    """
    try:
        verifier = base_64_urlencode(secrets.token_bytes(32))
        challenge = base_64_urlencode(sha256(verifier))
        # Removes the padding character if one is used, Auth0 bugs out if this is left in.
        challenge_str = re.sub('=$', '', challenge.decode()).encode('utf-8')
        return verifier, challenge_str
    except TypeError as tye:
        print(tye)


def authorize_user(challenge_str) -> None:
    """
    Generates an oauth URL and directs the user to it.

    Arguments:
        challenge_str {str} -- String representation of the challenge.
    """
    params = {
        'audience': AUDIENCE,
        'scope': SCOPE,
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'code_challenge': challenge_str,
        'code_challenge_method': CODE_CHALLENGE_METHOD,
        'redirect_uri': REDIRECT_URI
    }
    try:
        url = DOMAIN + urllib.parse.urlencode(params)
        webbrowser.open(url)
    except TypeError as tye:
        print(tye)


def exchange_code_for_token(code: str, verifier: bytes) -> str:
    """
    Exchanges the code for an access token to use with the API.

    Arguments:
        code {str} -- Code from google
        verifier {bytes} -- verifier that was used to generate the challenge.

    Returns:
        str -- Access token for use with the API.
    """
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'code_verifier': verifier,
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    res = requests.post("https://cidc-test.auth0.com/oauth/token", json=payload)

    if not res.status_code == 200:
        print("Error exchanging code for token")
        print(res.reason)
        return None

    res_json = res.json()

    return res_json['access_token']


def send_response_html(connection, status: bool) -> None:
    """
    Sends HTML to tell the user whether or not the authentication worked.

    Arguments:
        connection {[type]} -- [description]
        status {bool} -- [description]

    Returns:
        None -- [description]
    """
    if status:
        connection.send(bytes('HTTP/1.1 200 OK\n', 'utf-8'))
        connection.send(bytes('Content-Type: text/html\n', 'utf-8'))
        connection.send(bytes('\n', 'utf-8'))
        connection.send(bytes("""
            <html>
            <body>
            <h1>Authentication Succeeded! Return to CLI.</h1>
            </body>
            </html>
        """, 'utf-8'))
    else:
        connection.send(bytes('HTTP/1.1 401 UNAUTHORIZED\n', 'utf-8'))
        connection.send(bytes('Content-Type: text/html\n', 'utf-8'))
        connection.send(bytes('\n', 'utf-8'))
        connection.send(bytes("""
            <html>
            <body>
            <h1>Authentication Failed: </h1>
            </body>
            </html>
        """, 'utf-8'))


def run_auth_proc() -> str:
    """
    Function in charge of running the authorization

    Returns:
        str -- Access token for the API
    """
    # Create cryptographic key.
    verifier, challenge_str = create_crypto_pair()

    # Open link and have user log in.
    authorize_user(challenge_str)

    # Listen for response from the login.
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sleep = 0
    while True and sleep < 10:
        try:
            serversocket.bind(('localhost', 5001))
            break
        except OSError as oser:
            print('failed to bind!')
            print(oser)
            time.sleep(1)
            sleep += 1

    if sleep == 10:
        print('Failed to connect, exiting!')
        serversocket.close()
        return None

    serversocket.listen(5)
    response = None

    # Keep connection alive until response.
    while True:
        connection, address = serversocket.accept()
        buf = connection.recv(1024)
        try:
            if len(buf) > 0:
                # When response received, take value, send response, then close.
                response = buf
                response_str = response.decode('utf-8')
                if re.search(r'get_code\?code=(\w+)', response_str).group(1):
                    code = re.search(r'get_code\?code=(\w+)', response_str).group(1)
                    try:
                        token = exchange_code_for_token(code, verifier)
                        send_response_html(connection, True)
                        return token
                    except RuntimeError:
                        # Testing to see if this fixes the auth thing. It may wait for *some*
                        # attempt to redeem the code, so lets hard-fail it, so it starts fresh.
                        exchange_code_for_token('failed_exchange', verifier)
                        send_response_html(connection, False)
                        break
            else:
                print('nothing....')
                break
        except OSError as error:
            print('OS ERROR: ' + error)
            exchange_code_for_token('failed_exchange', verifier)
            send_response_html(connection, False)
        finally:
            serversocket.close()
    return None
