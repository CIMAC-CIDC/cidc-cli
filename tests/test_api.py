from io import BytesIO

import pytest
from unittest.mock import MagicMock
from typing import Union

from cli import api, config, __version__


def make_json_response(body={}) -> MagicMock:
    response = MagicMock()
    response.json.return_value = body
    response.status_code = 200
    return response


def make_error_response(msg: Union[str, list], code: int = 400) -> MagicMock:
    response = make_json_response({'_error': {'message': msg}})
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

    # Error response without message
    response = MagicMock()
    response.json.side_effect = Exception()
    response.status_code = 503
    assert 'API server encountered an error' in api._error_message(response)

    MSG = ["first", "another"]
    response = make_error_response(MSG)
    for m in MSG:
        assert m in api._error_message(response)

    # Error response without proper json _error message
    response = MagicMock()
    response.json.side_effect = Exception()
    response.status_code = 503
    assert 'API server encountered an error' in api._error_message(response)

    # Error response without proper json _error and 4xx code
    response = MagicMock()
    response.json.side_effect = Exception()
    response.status_code = 403
    assert 'API server encountered an error' in api._error_message(response)


def test_with_auth(monkeypatch):
    """Test the authorization header builder"""
    TOKEN = 'tok'
    AUTH_HEADER = {
        'Authorization': f'Bearer {TOKEN}',
        'User-Agent': f'cidc-cli/{__version__}'
    }
    OTHER_HEADERS = {
        'If-Match': 'blah blah blah',
        'Content-Type': 'application/json'
    }
    HEADERS = {**OTHER_HEADERS, **AUTH_HEADER}

    assert api._with_auth(id_token=TOKEN) == AUTH_HEADER
    assert api._with_auth(headers=OTHER_HEADERS, id_token=TOKEN) == HEADERS

    monkeypatch.setattr('cli.auth.get_id_token', lambda: TOKEN)
    assert api._with_auth() == AUTH_HEADER
    assert api._with_auth(headers=OTHER_HEADERS) == HEADERS


def test_check_auth(monkeypatch):
    """Check that api.check_auth handles errors as expected"""
    # Auth error
    ERR = 'signature expired'
    not_authorized = make_error_response(ERR, 401)
    patch_request('get', not_authorized, monkeypatch)
    with pytest.raises(api.ApiError, match=ERR):
        api.check_auth('foo_token')

    # Successful authorization
    success = make_json_response()
    patch_request('get', success, monkeypatch)
    assert api.check_auth('foo_token') is None


def test_list_assays(monkeypatch):
    assays = ['wes', 'pbmc']
    response = make_json_response(assays)
    patch_request('get', response, monkeypatch)
    assert api.list_assays() == assays


JOB_ID = 1
JOB_ETAG = 'abcd'


def test_initiate_assay_upload(monkeypatch):
    """Test upload initation builds a request and parses a response correctly"""
    ASSAY = 'wes'
    XLSX = BytesIO(b'abcd')
    GCS_BUCKET = 'bucket'
    URL_MAPPING = {'foo': 'bar'}
    EXTRA_METADATA = {'uuid': 'lp1'}

    monkeypatch.setattr(api, '_with_auth', lambda: {})

    def good_request(url, headers, data, files):
        assert data.get('schema') == 'wes'
        assert files.get('template') == XLSX
        return make_json_response({
            'job_id': JOB_ID,
            'job_etag': JOB_ETAG,
            'gcs_bucket': GCS_BUCKET,
            'url_mapping': URL_MAPPING,
            'extra_metadata': EXTRA_METADATA
        })

    monkeypatch.setattr('requests.post', good_request)
    api.initiate_assay_upload(ASSAY, XLSX)

    ERR = 'bad request or something'
    bad_request = make_error_response(ERR, 400)
    patch_request('post', bad_request, monkeypatch)
    with pytest.raises(api.ApiError, match=ERR):
        api.initiate_assay_upload(ASSAY, XLSX)

    BADLY_TYPED_ERR = [ERR]
    bad_request = make_error_response(BADLY_TYPED_ERR, 400)
    patch_request('post', bad_request, monkeypatch)
    with pytest.raises(api.ApiError, match=ERR):
        api.initiate_assay_upload(ASSAY, XLSX)

    cant_decode = make_json_response({'foo': 'bar'})
    patch_request('post', cant_decode, monkeypatch)
    with pytest.raises(api.ApiError, match='Cannot decode API response'):
        api.initiate_assay_upload(ASSAY, XLSX)


def test_update_job_status(monkeypatch):
    """Test that _update_job_status builds a request with the expected structure"""
    monkeypatch.setattr(api, '_with_auth', lambda headers: headers)

    def test_status(status):
        def request(url, json, headers):
            assert url.endswith(str(JOB_ID))
            assert json == {'status': status}
            assert headers.get('If-Match') == JOB_ETAG
            return make_json_response()
        return request

    monkeypatch.setattr('requests.patch', test_status('upload-completed'))
    api.assay_upload_succeeded(JOB_ID, JOB_ETAG)

    monkeypatch.setattr('requests.patch', test_status('upload-failed'))
    api.assay_upload_failed(JOB_ID, JOB_ETAG)


def test_poll_upload_merge_status(monkeypatch):
    """Check that poll_upload_merge status handles various responses as expected"""
    monkeypatch.setattr(api, '_with_auth', lambda: {})

    def not_found_get(*args, **kwargs):
        return make_error_response("", code=404)

    monkeypatch.setattr('requests.get', not_found_get)
    with pytest.raises(api.ApiError):
        api.poll_upload_merge_status(1)

    def bad_response_get(*args, **kwargs):
        return make_json_response({})

    monkeypatch.setattr('requests.get', bad_response_get)
    with pytest.raises(api.ApiError, match='unexpected upload status message'):
        api.poll_upload_merge_status(1)

    def good_retry_get(*args, **kwargs):
        return make_json_response({'retry_in': 5})

    monkeypatch.setattr('requests.get', good_retry_get)
    upload_status = api.poll_upload_merge_status(1)
    assert upload_status.retry_in == 5
    assert upload_status.status is None
    assert upload_status.status_details is None

    status_res = {'status': 'merge-failed',
                  'status_details': 'error message here'}

    def good_status_get(*args, **kwargs):
        return make_json_response(status_res)

    monkeypatch.setattr('requests.get', good_status_get)
    upload_status = api.poll_upload_merge_status(1)
    assert upload_status.retry_in is None
    assert upload_status.status == status_res['status']
    assert upload_status.status_details == status_res['status_details']
