#!/usr/bin/env python3
"""
Defines caching before for user preferences
"""

from cachetools import TTLCache


class CredentialCache(TTLCache):
    """
    Subclass of TTLCache that temporarily stores and retreives user login credentials

    Arguments:
        TTLCache {TTLCache} -- A TTLCache object

    Returns:
        CredentialCache -- [description]
    """
    def add_login_to_cache(self, username, token):
        """
        Add user's credentials to the cache

        Arguments:
            username {string} -- user's name
            token {string} -- eve access token
        """
        self['username'] = username
        self['token'] = token

    def get_login(self):
        """
        Retreives the login credentials, or an empty dict if not found

        Returns:
            dict -- Dict containing user information
        """
        if 'username' in self and 'token' in self:
            return {
                'username': self['username'],
                'token': self['token']
            }
        else:
            return {}

    def get_jobs(self):
        """
        Returns job objects 
        Returns:
            [type] -- [description]
        """
        if 'jobs' not in self:
            return None

        return self['jobs']

    def add_job_to_cache(self, job_id):
        """
        Adds a job ID to cache for easy retreival and status querying.

        Arguments:
            job_id {[type]} -- [description]
        """
        if 'jobs' not in self:
            self['jobs'] = []

        self['jobs'].append(job_id)
