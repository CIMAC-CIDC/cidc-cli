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
    def cache_key(self, key):
        """
        Adds an access key to the cache

        Arguments:
            key {str} -- Google access token.
        """
        self['access_token'] = key

    def get_key(self) -> str:
        """
        Retreive key from cache.
        """
        if 'access_token' in self:
            return self['access_token']

        return

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
