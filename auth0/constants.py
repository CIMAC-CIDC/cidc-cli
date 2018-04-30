"""[summary]
"""
from os import environ as env
from dotenv import find_dotenv, load_dotenv

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

DOMAIN = env.get('DOMAIN')
AUDIENCE = env.get('AUDIENCE')
CLIENT_ID = env.get('CLIENT_ID')
CODE_CHALLENGE_METHOD = env.get('CODE_CHALLENGE_METHOD')
REDIRECT_URI = env.get('REDIRECT_URI')
SCOPE = env.get('SCOPE')
EVE_URL = env.get('EVE_URL')
