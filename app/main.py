import asyncio
import base64
import json
import os
import secrets
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from . import store
from .schemas import TestInput, ExperimentInput, ChatInput
from .media import preview, source_url
from .providers import Provider, ProviderError
from .simulation import execute, cached
from .network import network_summary, initial_network

jobs = {}
chat_jobs = set()
semaphore = None
@asynccontextmanager
async def lifespan(app):
    global semaphore
    store.init()
    semaphore = asyncio.Semaphore(max(1,min(10,int(os.getenv('AGENT_CONCURRENCY','1')))))
    yield
    tasks = list(jobs.values())
    for t in tasks: t.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)
    store.close()

app = FastAPI(title='Ripple',version='2.0.0',lifespan=lifespan,docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','[::1]','testserver'])

@app.middleware('http')
async def security(request: Request, call_next):
    password = os.getenv('APP_PASSWORD','')
    if password:
        try:
            method, value = request.headers.get('authorization','').split(' ',1)
            username, supplied = base64.b64decode(value).decode().split(':',1)
            valid = method.lower()=='basic' and secrets.compare_digest(supplied,password)
        except Exception: valid = False
        if not valid: return JSONResponse({'detail':'Local password required.'},401,headers={'WWW-Authenticate':'Basic realm="Ripple"'})
    if request.method in ('POST','DELETE','PUT','PATCH'):
        origin = request.headers.get('origin')
        if (origin and origin != str(request.base_url).rstrip('/')) or request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Cross-origin requests are not allowed.'},403)
        if request.headers.get('x-ripple-client')!='1':
            return JSONResponse({'detail':'Missing same-origin request marker.'},403)
    limit = int(os.getenv('MAX_UPLOAD_MB','100'))*1024*1024+1024*1024
    try: length = int(request.headers.get('content-length','0'))
    except ValueError: return JSONResponse({'detail':'Invalid content length'},400)
    if length>limit: return JSONResponse({'detail':'Upload exceeds configured size limit.'},413)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"})
    return response

class BodyLimit:
    """Bound streamed/chunked request bodies before multipart parsing allocates disk."""
    def __init__(self, app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        size=0
        async def limited():
            nonlocal size
            message=await receive()
            if message['type']=='http.request':
                size+=len(message.get('body',b''))
                if size>int(os.getenv('MAX_UPLOAD_MB','100'))*1024*1024+1024*1024:
                    raise HTTPException(413,'Upload exceeds configured size limit.')
            return message
        await self.app(scope,limited,send)
app.add_middleware(BodyLimit)

BASE = Path(__file__).parent
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
@app.get('/')
async def index(): return FileResponse(BASE/'static'/'index.html')

@app.get('/api/config')
async def config():
    warnings=[]
    if os.getenv('GROQ_API_KEY'):
        try: Provider('groq')
        except ProviderError as exc: warnings.append(str(exc))
    if os.getenv('GROQ_TRANSCRIPTION_MODEL','').startswith('gsk_'):
        warnings.append('Your Groq key is in GROQ_TRANSCRIPTION_MODEL. Move it to GROQ_API_KEY; restore whisper-large-v3-turbo as the transcription model.')
    return {'version':'2.0.0','providers':{'groq':bool(os.getenv('GROQ_API_KEY','').strip())},'defaultProvider':'groq','ffmpeg':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),'maxUploadMB':int(os.getenv('MAX_UPLOAD_MB','100')),'maxDuration':int(os.getenv('MAX_DURATION_SECONDS','180')),'warnings':warnings,'concurrency':max(1,min(10,int(os.getenv('AGENT_CONCURRENCY','1')))),'requestInterval':float(os.getenv('REQUEST_INTERVAL_SECONDS','4'))}

@app.post('/api/providers/{name}/check')
async def provider_check(name: str):
    if name!='groq': raise HTTPException(422,'Model discovery currently supports Groq.')
    try: return await Provider(name).models()
    except ProviderError as exc: raise HTTPException(422,str(exc))
    except Exception: raise HTTPException(502,'Could not connect to Groq model discovery. Check connectivity and try again.')


@app.post('/api/preview')
async def source(request: Request):
    data = await request.json()
    try: return await preview(str(data.get('url',''))[:2000])
    except ValueError as exc: raise HTTPException(422,str(exc))

@app.get('/api/tests')
async def tests(): return store.listing()

def find(id):
    row = store.get(id)
    if row is None: raise HTTPException(404,'Test not found')
    return row

def launch(id):
    task = asyncio.create_task(execute(id,semaphore))
    jobs[id]=task
    task.add_done_callback(lambda _:jobs.pop(id,None))

@app.post('/api/tests', status_code=202)
async def create(payload: str = Form(...), video: UploadFile | None = File(None)):
    if len(jobs)>=2: raise HTTPException(429,'Two tests are already running. Wait before starting another.')
    try:
        data = TestInput.model_validate_json(payload)
        Provider(data.provider)
        if data.sourceType=='link':
            source_url(data.url)
            if not data.transcript.strip() and not data.caption.strip():
                raise ValueError('For links, supply a transcript or caption, or upload the video instead.')
        elif not video: raise ValueError('Select a video file.')
    except (ValidationError, ValueError, ProviderError) as exc:
        raise HTTPException(422,str(exc))
    id = str(uuid.uuid4())
    directory=store.MEDIA/id
    directory.mkdir(mode=0o700)
    try:
        if data.sourceType=='upload':
            suffix=Path(video.filename or '').suffix.lower()
            if suffix not in ('.mp4','.mov','.webm'): raise HTTPException(422,'Supported formats: MP4, MOV and WebM.')
            size=0
            with (directory/('source'+suffix)).open('wb') as f:
                while chunk := await video.read(1024*1024):
                    size+=len(chunk)
                    if size>int(os.getenv('MAX_UPLOAD_MB','100'))*1024*1024: raise HTTPException(413,'Video is too large.')
                    f.write(chunk)
            if not size: raise HTTPException(422,'Video is empty.')
        store.create(id,data.model_dump())
        launch(id)
        return {'id':id}
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise
    finally:
        if video: await video.close()

@app.get('/api/tests/{id}')
async def get(id: str):
    row=find(id)
    row['version']=cached(store.MEDIA/id,'experiment.json')
    return row

@app.post('/api/tests/{id}/retry')
async def retry(id: str):
    row=find(id)
    if id in jobs: raise HTTPException(409,'Test is already running.')
    if len(jobs)>=2: raise HTTPException(429,'Two tests are already running.')
    if row['status'] not in ('failed','partial','interrupted'): raise HTTPException(409,'Only failed, interrupted or partial tests can be retried.')
    try: Provider('groq')
    except ProviderError as exc: raise HTTPException(422,str(exc))
    store.update(id,status='queued',error=None)
    launch(id)
    return {'id':id}

@app.delete('/api/tests/{id}')
async def delete(id: str):
    find(id)
    if id in jobs or id in chat_jobs: raise HTTPException(409,'Wait for the running request to finish before deleting.')
    store.delete(id)
    shutil.rmtree(store.MEDIA/id,ignore_errors=True)
    return {'deleted':True}

@app.get('/api/tests/{id}/frames/{name}')
async def frame(id: str,name: str):
    find(id)
    import re
    if not re.fullmatch(r'frame-\d+\.jpg',name): raise HTTPException(404)
    path=store.MEDIA/id/name
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path,media_type='image/jpeg')

@app.get('/api/tests/{id}/export')
async def export(id: str):
    row=find(id)
    row['version']=cached(store.MEDIA/id,'experiment.json')
    row['liveNetwork']=await live_test(id)
    return JSONResponse(row,headers={'Content-Disposition':f'attachment; filename="ripple-{id}.json"'})


@app.get('/api/tests/{id}/live')
async def live_test(id: str):
    row=find(id)
    directory=store.MEDIA/id
    live=cached(directory,'live.json')
    if live is None:
        # Old v1 tests keep their results; no artificial exposure history is invented.
        profiles=cached(directory,'profiles.json') or (row.get('result') or {}).get('profiles',[])
        live=initial_network(profiles)
        responses=cached(directory,'responses.json') or {}
        for node in live['nodes']:
            r=responses.get(node['id'])
            if r: node.update(status='completed',reaction=r,exposure='legacy',wave=None)
        live['legacy']=bool(responses)
        live['complete']=row['status'] in ('completed','partial')
    live['summary']=network_summary(live)
    live['status']=row['status'];live['stage']=row['stage'];live['progress']=row['progress']
    return live

@app.get('/api/tests/{id}/video')
async def private_video(id: str):
    row=find(id)
    if row['payload']['sourceType']!='upload': raise HTTPException(404,'No uploaded video')
    paths=list((store.MEDIA/id).glob('source.*'))
    if not paths: raise HTTPException(404,'Video unavailable')
    path=paths[0]
    return FileResponse(path,media_type={'.mp4':'video/mp4','.mov':'video/quicktime','.webm':'video/webm'}.get(path.suffix,'application/octet-stream'))

@app.post('/api/tests/{id}/versions',status_code=202)
async def experiment(id: str, payload: ExperimentInput):
    from .experiments import create_version
    row=find(id)
    if row['status'] not in ('completed','partial'): raise HTTPException(409,'Finish the original simulation first.')
    if id in jobs or len(jobs)>=2: raise HTTPException(429,'Wait for running simulations to finish.')
    try:
        Provider('groq')
        child=create_version(row,payload)
    except (ValueError,ProviderError) as exc: raise HTTPException(422,str(exc))
    launch(child)
    return {'id':child}

@app.get('/api/tests/{id}/compare/{other}')
async def comparison(id: str, other: str):
    from .experiments import compare
    try: return compare(find(id),find(other))
    except ValueError as exc: raise HTTPException(409,str(exc))

@app.get('/api/tests/{id}/versions')
async def version_history(id: str):
    row=find(id)
    version=cached(store.MEDIA/id,'experiment.json') or {}
    root=version.get('rootId',id)
    versions=[]
    for candidate in store.listing():
        metadata=cached(store.MEDIA/candidate['id'],'experiment.json') or {}
        if candidate['id']==root or metadata.get('rootId')==root:
            versions.append(dict(candidate,parentId=metadata.get('parentId')))
    return versions

@app.get('/api/tests/{id}/chat')
async def conversation(id: str):
    find(id)
    return cached(store.MEDIA/id,'chat.json') or []

@app.post('/api/tests/{id}/chat')
async def ask(id: str,payload: ChatInput):
    from .agents.chat import answer
    row=find(id)
    if not row.get('result'): raise HTTPException(409,'Complete a simulation before asking Ripple.')
    if id in chat_jobs: raise HTTPException(409,'A reply is already being prepared for this simulation.')
    if len(chat_jobs)>=2: raise HTTPException(429,'Two replies are already running. Try again shortly.')
    chat_jobs.add(id)
    try: return await answer(row,payload.message,Provider('groq'),semaphore)
    except ProviderError as exc: raise HTTPException(502,str(exc))
    finally: chat_jobs.discard(id)

@app.get('/api/tests/{id}/report')
async def report(id: str):
    from .reports import creator_report
    row=find(id)
    if not row.get('result'): raise HTTPException(409,'A report needs saved simulation results.')
    return Response(creator_report(row),media_type='text/markdown',headers={'Content-Disposition':f'attachment; filename="ripple-{id}-report.md"'})
