import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.providers import Provider, ProviderError

TOOLS = [{'type':'function','function':{'name':'read_file','description':'Read reviewed skill',
          'parameters':{'type':'object','properties':{'file_path':{'type':'string'}},'required':['file_path']}}}]


@pytest.mark.parametrize('name',['groq','gemini'])
def test_native_tool_transport_roundtrip(monkeypatch, name):
    monkeypatch.setenv(name.upper()+'_API_KEY','test-key')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    bodies=[]
    parts=[{'functionCall':{'id':'gemini-call-id','name':'read_file','args':{'file_path':'/skills/panel-synthesis/SKILL.md'}},
            'thoughtSignature':'signature-from-provider'}]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,**kw):
            bodies.append(kw['json'])
            if name=='groq':
                value={'choices':[{'finish_reason':'tool_calls','message':{'content':None,
                    'tool_calls':[{'id':'native-id','type':'function','function':{'name':'read_file',
                    'arguments':json.dumps({'file_path':'/skills/panel-synthesis/SKILL.md'})}}]}}]}
            else: value={'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':parts}}]}
            return httpx.Response(200,json=value)
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    async def check():
        p=Provider(name)
        messages=[{'role':'system','content':'Review evidence.'},{'role':'user','content':'Begin'}]
        response, native = await p.tool_call(messages,TOOLS,required=True)
        assert response.toolCalls[0].name=='read_file'
        messages += [{'role':'assistant','content':'','tool_calls':[{'id':'local-id','type':'function',
            'function':{'name':response.toolCalls[0].name,'arguments':response.toolCalls[0].arguments}}],
            '_geminiParts':native}, {'role':'tool','tool_call_id':'local-id','name':'read_file','content':'Reviewed skill text'}]
        await p.tool_call(messages,TOOLS)
    asyncio.run(check())
    if name=='groq':
        assert bodies[0]['tool_choice']=={'type':'function','function':{'name':'read_file'}}
        assert bodies[0]['parallel_tool_calls'] is False and 'response_format' not in bodies[0]
        assert bodies[1]['messages'][-1]['tool_call_id']=='local-id'
        assert '_geminiParts' not in bodies[1]['messages'][-2]
    else:
        assert bodies[0]['tools'][0]['functionDeclarations'][0]['parametersJsonSchema']
        assert bodies[0]['toolConfig']['functionCallingConfig']['mode']=='ANY'
        assert bodies[1]['contents'][-2]['parts']==parts
        assert bodies[1]['contents'][-1]['parts'][0]['functionResponse']['name']=='read_file'
        assert bodies[1]['contents'][-1]['parts'][0]['functionResponse']['id']=='gemini-call-id'


def test_native_tool_quota_and_redaction(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-secret')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    calls=[]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            calls.append(1)
            return httpx.Response(429,headers={'retry-after':'900'},json={'error':{'message':'PRIVATE test-secret'}})
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    with pytest.raises(ProviderError) as exc:
        asyncio.run(Provider('groq').tool_call([{'role':'user','content':'test'}],TOOLS))
    assert exc.value.fatal and exc.value.retry_after==900 and len(calls)==1
    assert 'PRIVATE' not in str(exc.value) and 'test-secret' not in str(exc.value)


def test_native_malformed_arguments_retry(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-secret')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    monkeypatch.setenv('MAX_PROVIDER_ATTEMPTS','2')
    calls=[]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            calls.append(1)
            return httpx.Response(200,json={'choices':[{'message':{'tool_calls':[
                {'function':{'name':'read_file','arguments':'[]' if len(calls)==1 else '{"file_path":"/skills/panel-synthesis/SKILL.md"}'}}]}}]})
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    monkeypatch.setattr('app.providers.asyncio.sleep',AsyncMock())
    response,_=asyncio.run(Provider('groq').tool_call([{'role':'user','content':'test'}],TOOLS))
    assert response.toolCalls[0].name=='read_file' and len(calls)==2


def test_native_output_parse_failure_retries_without_echoing_provider_body(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-secret')
    monkeypatch.setenv('REQUEST_INTERVAL_SECONDS','0')
    monkeypatch.setenv('MAX_PROVIDER_ATTEMPTS','2')
    bodies=[]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            bodies.append(kwargs['json'])
            if len(bodies)==1:
                return httpx.Response(400,json={'error':{'code':'output_parse_failed',
                    'message':'PRIVATE test-secret', 'failed_generation':'PRIVATE generated content'}})
            return httpx.Response(200,json={'choices':[{'message':{'tool_calls':[
                {'function':{'name':'read_file','arguments':'{"file_path":"/skills/panel-synthesis/SKILL.md"}'}}]}}]})
    monkeypatch.setattr('app.providers.httpx.AsyncClient',lambda **kw:Client())
    response,_=asyncio.run(Provider('groq').tool_call([{'role':'user','content':'test'}],TOOLS,required=True))
    assert response.toolCalls[0].name=='read_file' and len(bodies)==2
    correction=bodies[1]['messages'][-1]['content']
    assert 'read_file' in correction and 'not executed' in correction
    assert 'PRIVATE' not in correction and 'test-secret' not in correction
