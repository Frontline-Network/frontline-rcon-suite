"""Language-management permissions use existing RCON roles and read/write verbs."""
import json
import os
from types import SimpleNamespace
import pytest
from tests.test_player_languages import database, EOS
from rcon import player_language as languages


@pytest.fixture
def request_api(database,monkeypatch):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','rconweb.settings')
    import django
    django.setup()
    from django.test import RequestFactory
    from api import views,auth,decorators
    from rcon.api_commands import RconAPI
    monkeypatch.setattr(auth,'check_api_key',lambda request:None)
    monkeypatch.setattr(views,'audit',lambda *a,**k:None)
    monkeypatch.setattr(decorators,'ENDPOINT_HTTP_METHODS',{})
    monkeypatch.setattr(decorators,'ENDPOINT_PERMISSIONS_LOOKUP',{})
    instance=RconAPI.__new__(RconAPI)
    endpoints={}
    def call(name,method='GET',values=None,perms=(),authenticated=True):
        func=getattr(instance,name)
        reference=getattr(views.rcon_api,name)
        if name not in endpoints:
            endpoints[name]=views.expose_api_endpoint(func,name,views.ENDPOINT_PERMISSIONS[reference],{func:views.RCON_ENDPOINT_HTTP_METHODS[reference]})
        endpoint=endpoints[name]
        request=getattr(RequestFactory(),method.lower())('/api/'+name,
            data=json.dumps(values or {}) if method=='POST' else (values or {}),content_type='application/json')
        request.user=SimpleNamespace(username='TestAdmin',is_authenticated=authenticated,is_active=True,
                                     has_perm=lambda p:p in perms,has_perms=lambda ps:all(p in perms for p in ps))
        return endpoint(request)
    return call


def test_profile_edits_require_account_edit_permission_and_post(request_api):
    payload={'player_id':EOS,'language':'fr'}
    assert request_api('set_player_language','POST',payload).status_code==403
    assert request_api('set_player_language','POST',payload,authenticated=False).status_code==401
    assert request_api('set_player_language','GET',payload,['api.can_edit_player_account']).status_code==405
    assert languages.get_profile(EOS)['language']=='de+en'
    response=request_api('set_player_language','POST',payload,['api.can_edit_player_account'])
    assert response.status_code==200 and json.loads(response.content)['result']['language']=='fr'
    assert request_api('get_player_language',values={'player_id':EOS}).status_code==403
    response=request_api('get_player_language',values={'player_id':EOS},perms=['api.can_view_player_profile'])
    assert json.loads(response.content)['result']['language']=='fr'


def test_catalog_preview_and_write_roles_are_distinct(request_api):
    assert request_api('get_player_message_catalog').status_code==403
    response=request_api('get_player_message_catalog',perms=['api.can_view_message_templates'])
    assert response.status_code==200 and json.loads(response.content)['result']['templates']
    payload={'key':'automod.no_leader.warning','source':'x','translations':{},'expected_revision':'x'}
    assert request_api('set_player_message_translations','POST',payload,['api.can_view_message_templates']).status_code==403
    response=request_api('set_player_language_settings','POST',{'enabled':'false'},['api.can_edit_message_templates'])
    assert json.loads(response.content)['failed'] is True
