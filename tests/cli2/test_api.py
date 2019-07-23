from io import BytesIO

import pytest
from unittest.mock import MagicMock

from cli2 import api, config


def make_response(body={}) -> MagicMock:
    response = MagicMock()
    response.json.return_value = body
    response.status_code = 200
    return response


def make_error_response(msg: str, code: int = 400) -> MagicMock:
    response = make_response({'_error': {'message': msg}})
    response.status_code = code
    return response


def patch_request(http_verb, response, monkeypatch):
    monkeypatch.setattr(f'requests.{http_verb}',
                        lambda *args, **kwargs: response)


def test_url_builder():
    base_url = config.API_V2_URL + '/'
    assert api._url("") == base_url
    assert api._url("/a") == base_url + 'a'
    assert api._url("a") == base_url + 'a'


def test_error_message_extractor():
    MSG = 'an error message'
    response = make_error_response(MSG)
    assert api._error_message(response) == MSG


def test_with_auth(monkeypatch):
    """Test the authorization header builder"""
    TOKEN = 'tok'
    AUTH_HEADER = {
        'Authorization': f'Bearer {TOKEN}'
    }
    OTHER_HEADERS = {
        'If-Match': 'blah blah blah',
        'Content-Type': 'application/json'
    }
    HEADERS = {**OTHER_HEADERS, **AUTH_HEADER}

    assert api._with_auth(id_token=TOKEN) == AUTH_HEADER
    assert api._with_auth(headers=OTHER_HEADERS, id_token=TOKEN) == HEADERS

    monkeypatch.setattr('cli2.auth.get_id_token', lambda: TOKEN)
    assert api._with_auth() == AUTH_HEADER
    assert api._with_auth(headers=OTHER_HEADERS) == HEADERS


def test_check_auth(monkeypatch):
    """Check that api.check_auth handles errors as expected"""
    # Auth error
    ERR = 'signature expired'
    not_authorized = make_error_response(ERR, 401)
    patch_request('get', not_authorized, monkeypatch)
    assert api.check_auth('foo_token') == ERR

    # Unexpected error
    other_error = make_error_response(ERR, 500)
    patch_request('get', other_error, monkeypatch)
    with pytest.raises(api.ApiError, match="unexpected error"):
        api.check_auth('foo_token')

    # Successful authorization
    success = make_response()
    patch_request('get', success, monkeypatch)
    assert api.check_auth('foo_token') is None


def test_list_assays(monkeypatch):
    assays = ['wes', 'pbmc']
    response = make_response(assays)
    patch_request('get', response, monkeypatch)
    assert api.list_assays() == assays


JOB_ID = 1
JOB_ETAG = 'abcd'


def test_initiate_upload(monkeypatch):
    """Test upload initation builds a request and parses a response correctly"""
    ASSAY = 'wes'
    XLSX = BytesIO(b'abcd')
    GCS_BUCKET = 'bucket'
    URL_MAPPING = {'foo': 'bar'}

    monkeypatch.setattr(api, '_with_auth', lambda: {})

    def good_request(url, headers, data, files):
        assert data.get('schema') == 'wes'
        assert files.get('template') == XLSX
        return make_response({
            'job_id': JOB_ID,
            'job_etag': JOB_ETAG,
            'gcs_bucket': GCS_BUCKET,
            'url_mapping': URL_MAPPING
        })

    monkeypatch.setattr('requests.post', good_request)
    api.initiate_upload(ASSAY, XLSX)

    ERR = 'bad request or something'
    bad_request = make_error_response(ERR, 400)
    patch_request('post', bad_request, monkeypatch)
    with pytest.raises(api.ApiError, match=ERR):
        api.initiate_upload(ASSAY, XLSX)

    cant_decode = make_response({'foo': 'bar'})
    patch_request('post', cant_decode, monkeypatch)
    with pytest.raises(api.ApiError, match='Cannot decode API response'):
        api.initiate_upload(ASSAY, XLSX)


def test_update_job_status(monkeypatch):
    """Test that _update_job_status builds a request with the expected structure"""
    monkeypatch.setattr(api, '_with_auth', lambda headers: headers)

    def test_status(status):
        def request(url, json, headers):
            assert url.endswith(str(JOB_ID))
            assert json == {'status': status}
            assert headers.get('If-Match') == JOB_ETAG
            return make_response()
        return request

    monkeypatch.setattr('requests.patch', test_status('completed'))
    api.job_succeeded(JOB_ID, JOB_ETAG)

    monkeypatch.setattr('requests.patch', test_status('errored'))
    api.job_failed(JOB_ID, JOB_ETAG)
