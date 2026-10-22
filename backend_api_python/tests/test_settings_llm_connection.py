import os

import pytest
import requests

import app.services.llm as llm_module
from app.services.llm import LLMAPIError, LLMProvider, LLMService


@pytest.fixture
def service(monkeypatch):
    instance = LLMService('openai')
    monkeypatch.setattr(instance, 'get_api_key', lambda provider: 'saved-key')
    monkeypatch.setattr(instance, 'get_base_url', lambda provider: 'https://saved.example/v1')
    monkeypatch.setattr(instance, 'get_default_model', lambda provider: 'saved-model')
    return instance


@pytest.mark.parametrize('provider', [provider for provider in LLMProvider if provider != LLMProvider.CUSTOM])
def test_probe_uses_exact_draft_and_provider_without_persisting(service, monkeypatch, provider):
    service._provider_override = provider.value
    captured = []
    def call(*args, **kwargs):
        captured.append((args, kwargs))
        return 'OK'
    method = '_call_google_gemini' if provider == LLMProvider.GOOGLE else '_call_litellm' if provider == LLMProvider.LITELLM else '_call_openai_compatible'
    monkeypatch.setattr(service, method, call)
    before = dict(os.environ)
    assert service.test_connection(api_key='draft-key', base_url='https://draft.example/v1/', model='vendor/exact-model')['success']
    assert captured[0][0][1:] == ('vendor/exact-model', 0.0, 'draft-key', 'https://draft.example/v1', 20)
    if provider == LLMProvider.GOOGLE:
        assert captured[0][1] == {}
    elif provider == LLMProvider.LITELLM:
        assert captured[0][1] == {'use_json_mode': False}
    else:
        assert captured[0][1] == {'use_json_mode': False, 'max_tokens': 8}
    assert len(captured) == 1
    assert dict(os.environ) == before


def test_blank_key_reuses_saved_key(service, monkeypatch):
    monkeypatch.setattr(service, '_call_openai_compatible', lambda *args, **kwargs: 'OK' if args[3] == 'saved-key' else '')
    assert service.test_connection(api_key='')['success']


def test_openai_compatible_probe_limits_output_tokens(service, monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {'choices': [{'message': {'content': 'OK'}}]}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(service, '_llm_post', post)
    assert service.test_connection(
        api_key='draft-key',
        base_url='https://draft.example/v1',
        model='vendor/exact-model',
    )['success']
    assert captured['json_payload']['max_tokens'] == 8
    assert 'response_format' not in captured['json_payload']


def test_llm_post_does_not_inherit_system_proxy_when_disabled(service, monkeypatch):
    captured = {}

    class Session:
        trust_env = True

        def request(self, method, url, **kwargs):
            captured.update(url=url, trust_env=self.trust_env, kwargs=kwargs)
            return object()

        def close(self):
            pass

    monkeypatch.setattr(llm_module.requests, 'Session', Session)
    monkeypatch.setattr(llm_module.requests, 'post', lambda *args, **kwargs: pytest.fail('must use the configured Session'))
    monkeypatch.setattr(service, '_llm_proxy_url', lambda: '')
    monkeypatch.setattr(service, '_llm_use_system_proxy', lambda: False)

    service._llm_post('https://draft.example/v1/chat/completions', headers={}, json_payload={}, timeout=1)

    assert captured['trust_env'] is False


def test_custom_probe_uses_models_catalog_without_generating_text(service, monkeypatch):
    service._provider_override = 'custom'
    monkeypatch.setattr(service, 'get_api_key', lambda provider: 'draft-key')
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {'data': [{'id': 'vendor/exact-model'}]}

    def get(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return Response()

    monkeypatch.setattr(service, '_llm_get', get)
    monkeypatch.setattr(service, '_call_openai_compatible', lambda *args, **kwargs: pytest.fail('must not generate text'))

    result = service.test_connection(
        base_url='https://draft.example/v1',
        model='vendor/exact-model',
    )

    assert result == {'success': True, 'error_type': ''}
    assert captured['url'] == 'https://draft.example/v1/models'
    assert captured['kwargs']['headers']['Authorization'] == 'Bearer draft-key'


def test_local_custom_needs_no_key(service, monkeypatch):
    service._provider_override = 'custom'
    monkeypatch.setattr(service, 'get_api_key', lambda provider: '')
    monkeypatch.setattr(service, '_llm_get', lambda *args, **kwargs: type(
        'Response', (), {
            'status_code': 200,
            'json': staticmethod(lambda: {'data': [{'id': 'local-model'}]}),
        }
    )())
    assert service.test_connection(base_url='http://127.0.0.1:11434/v1', model='local-model')['success']


@pytest.mark.parametrize('kwargs,error', [
    ({'model': ''}, 'model_required'),
    ({'base_url': 'file:///tmp/test'}, 'invalid_url'),
    ({'base_url': 'http://[broken'}, 'invalid_url'),
    ({'base_url': 'https://user:secret@example.com/v1'}, 'invalid_url'),
    ({'base_url': 'https://example.com/v1?key=secret'}, 'invalid_url'),
])
def test_invalid_draft_does_not_send(service, monkeypatch, kwargs, error):
    monkeypatch.setattr(service, '_call_openai_compatible', lambda *a, **kw: pytest.fail('must not send'))
    assert service.test_connection(**kwargs) == {'success': False, 'error_type': error}


@pytest.mark.parametrize('status,error', [(401, 'authentication'), (402, 'payment_required'), (403, 'permission_denied'), (404, 'model_not_found'), (429, 'rate_limit_exceeded'), (503, 'provider_error')])
def test_provider_failure_is_safe_and_does_not_fallback(service, monkeypatch, status, error):
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise LLMAPIError('secret-key echoed upstream', status_code=status)
    monkeypatch.setattr(service, '_call_openai_compatible', fail)
    result = service.test_connection()
    assert result == {'success': False, 'error_type': error, 'status_code': status}
    assert len(calls) == 1
    assert 'secret' not in str(result)


def test_timeout_is_classified(service, monkeypatch):
    def fail(*args, **kwargs):
        raise requests.exceptions.Timeout('secret')
    monkeypatch.setattr(service, '_call_openai_compatible', fail)
    assert service.test_connection()['error_type'] == 'timeout'


def test_wrapped_timeout_is_classified(service, monkeypatch):
    def fail(*args, **kwargs):
        raise requests.exceptions.ConnectionError('secret') from requests.exceptions.Timeout('secret')
    monkeypatch.setattr(service, '_call_openai_compatible', fail)
    assert service.test_connection() == {'success': False, 'error_type': 'timeout'}


def test_google_http_error_is_safe(service, monkeypatch):
    service._provider_override = 'google'
    response = requests.Response()
    response.status_code = 403
    def fail(*args, **kwargs):
        raise requests.exceptions.HTTPError('secret-key', response=response)
    monkeypatch.setattr(service, '_call_google_gemini', fail)
    assert service.test_connection() == {'success': False, 'error_type': 'permission_denied', 'status_code': 403}


def test_missing_key_does_not_send(service, monkeypatch):
    monkeypatch.setattr(service, 'get_api_key', lambda provider: '')
    monkeypatch.setattr(service, '_call_openai_compatible', lambda *a, **kw: pytest.fail('must not send'))
    assert service.test_connection() == {'success': False, 'error_type': 'api_key_required'}


def test_empty_reply_is_not_success(service, monkeypatch):
    monkeypatch.setattr(service, '_call_openai_compatible', lambda *a, **kw: '  ')
    assert service.test_connection() == {'success': False, 'error_type': 'empty_response'}


@pytest.fixture
def admin(monkeypatch):
    import app.utils.auth as auth
    monkeypatch.setattr(auth, 'verify_token', lambda token: {
        'sub': 'admin', 'user_id': 1, 'role': 'admin',
        '_verified_username': 'admin', '_verified_user_role': 'admin',
    })
    return {'Authorization': 'Bearer test-token'}


def test_route_forwards_draft(client, admin, monkeypatch):
    captured = {}
    def probe(self, **kwargs):
        captured.update(provider=self.provider.value, **kwargs)
        return {'success': True, 'error_type': ''}
    monkeypatch.setattr(LLMService, 'test_connection', probe)
    response = client.post('/api/settings/test-connection', headers=admin, json={
        'service': 'llm', 'provider': 'custom', 'api_key': 'draft', 'base_url': 'http://localhost:11434/v1', 'model': 'local',
    })
    assert response.status_code == 200
    assert response.json['code'] == 1
    assert captured == {'provider': 'custom', 'api_key': 'draft', 'base_url': 'http://localhost:11434/v1', 'model': 'local'}
    assert 'draft' not in response.get_data(as_text=True)


def test_route_rejects_invalid_provider(client, admin):
    response = client.post('/api/settings/test-connection', headers=admin, json={'service': 'llm', 'provider': 'unknown'})
    assert response.status_code == 400


def test_route_requires_admin(client, monkeypatch):
    import app.utils.auth as auth
    monkeypatch.setattr(auth, 'verify_token', lambda token: {
        'sub': 'user', 'user_id': 2, 'role': 'user',
        '_verified_username': 'user', '_verified_user_role': 'user',
    })
    assert client.post('/api/settings/test-connection', headers={'Authorization': 'Bearer test'}, json={'service': 'llm', 'provider': 'openai'}).status_code == 403
