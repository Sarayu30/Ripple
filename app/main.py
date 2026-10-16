import asyncio
import json
import os
import shutil
import uuid
import hashlib
import secrets
from functools import wraps
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, JSONResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from . import store
from . import settings
from . import auth
from . import worker
from . import budgets
from .schemas import TestInput, ExperimentInput, ChatInput
from .media import preview, source_url
from .providers import Provider, ProviderError
from .simulation import execute, cached
from .network import network_summary, initial_network

jobs = {}
chat_jobs = set()
semaphore = None
submission_lock = None
queue_task = None
@asynccontextmanager
async def lifespan(app):
    global semaphore, submission_lock, queue_task
    settings.validate()
    await asyncio.to_thread(store.init)
    semaphore = asyncio.Semaphore(max(1,min(10,int(os.getenv('AGENT_CONCURRENCY','1')))))
    submission_lock = asyncio.Lock()
    connection = await asyncio.to_thread(worker.acquire)
    try:
        if worker.enabled():
            await asyncio.to_thread(worker.recover)
            queue_task = asyncio.create_task(worker.run(connection, jobs, start_job))
        else:
            with store.db() as c:
                c.execute("UPDATE tests SET status='interrupted', error='Server restarted. Resume saved work.' WHERE status IN ('queued','running')")
        yield
    finally:
        if queue_task:
            queue_task.cancel()
            await asyncio.gather(queue_task, return_exceptions=True)
            queue_task = None
        tasks = list(jobs.values())
        for t in tasks: t.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await asyncio.to_thread(connection.close)
        store.close()


def serial_submission(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        if submission_lock.locked():
            raise HTTPException(429, 'Another submission is being saved. Try again shortly.')
        async with submission_lock:
            return await function(*args, **kwargs)
    return wrapped

app = FastAPI(title='Ripple',version='2.0.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts())

@app.middleware('http')
async def security(request: Request, call_next):
    probe = request.method == 'GET' and request.url.path == '/healthz'
    header = request.headers.get('authorization', '')
    if settings.production() and not probe and not secrets.compare_digest(request.headers.get('x-ripple-origin-secret', ''), os.getenv('ORIGIN_SECRET', '')):
        return JSONResponse({'detail': 'Use the published application address.'}, 403, headers={'Cache-Control':'no-store'})
    if probe:
        user = 'public'
    elif auth.managed():
        token = header[7:] if header.startswith('Bearer ') else request.cookies.get('ripple_session', '')
        public = request.url.path in ('/', '/auth-config.js', '/api/auth/logout') or request.url.path.startswith('/static/')
        user = 'public' if public else await asyncio.to_thread(auth.verify_session, token)
    else:
        user = await asyncio.to_thread(auth.authenticate, request.headers.get('authorization', ''))
    if user is None:
        headers = {'Cache-Control': 'no-store'}
        if not auth.managed(): headers['WWW-Authenticate'] = 'Basic realm="Ripple", charset="UTF-8"'
        return JSONResponse({'detail':'Sign in to access your workspace.'},401,headers=headers)
    if request.method in ('POST','DELETE','PUT','PATCH'):
        origin = request.headers.get('origin')
        expected_origin = settings.public_origin() or str(request.base_url).rstrip('/')
        if (origin and origin != expected_origin) or request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Cross-origin requests are not allowed.'},403)
        if request.headers.get('x-ripple-client')!='1':
            return JSONResponse({'detail':'Missing same-origin request marker.'},403)
    limit = int(os.getenv('MAX_UPLOAD_MB','100'))*1024*1024+1024*1024
    try: length = int(request.headers.get('content-length','0'))
    except ValueError: return JSONResponse({'detail':'Invalid content length'},400)
    if length>limit: return JSONResponse({'detail':'Upload exceeds configured size limit.'},413)
    context_token = auth.identity.set(user)
    try:
        response = await call_next(request)
    finally:
        auth.identity.reset(context_token)
    response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','X-Frame-Options':'DENY','Content-Security-Policy': settings.csp()})
    if auth.managed() and header.startswith('Bearer ') and user != 'public':
        import jwt, time
        expires = jwt.decode(token, options={'verify_signature': False}).get('exp', 0)
        response.set_cookie('ripple_session', token, max_age=max(0, int(expires - time.time())),
                            httponly=True, secure=settings.production(), samesite='strict', path='/api')
    if settings.production():
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    if request.url.path.startswith('/static/') and response.status_code == 200:
        response.headers['Cache-Control'] = 'private, max-age=0, must-revalidate'
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
async def index():
    html = (BASE/'static'/'index.html').read_text(encoding='utf-8')
    return HTMLResponse(html.replace('/static/auth-config.js', '/auth-config.js'))

@app.get('/auth-config.js')
async def auth_config():
    config = auth.public_config() if auth.managed() else {'mode': 'local'}
    return Response('window.RipplePublicAuth = ' + json.dumps(config) + ';', media_type='application/javascript')

@app.post('/api/auth/session')
async def establish_session(): return {'authenticated': True}

@app.post('/api/auth/logout')
async def logout():
    response = JSONResponse({'signedOut': True})
    response.delete_cookie('ripple_session', path='/api', secure=settings.production(), httponly=True, samesite='strict')
    return response

@app.get('/api/health/live')
async def health_live(): return {'status': 'ok'}

@app.get('/healthz')
@app.get('/api/health/ready')
async def health_ready():
    def check():
        with store.db() as connection:
            connection.execute('SELECT 1')
        return os.access(store.MEDIA, os.W_OK) and bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
    try:
        queue_ready = not worker.enabled() or (queue_task is not None and not queue_task.done())
        if queue_ready and await asyncio.to_thread(check): return {'status': 'ready'}
    except Exception:
        pass
    return JSONResponse({'status': 'unavailable'}, 503)

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
def tests(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    return store.listing(limit, offset)

def find(id):
    row = store.get(id)
    if row is None: raise HTTPException(404,'Test not found')
    return row

def start_job(id):
    task = asyncio.create_task(execute(id,semaphore))
    jobs[id]=task
    task.add_done_callback(lambda _:jobs.pop(id,None))

def launch(id):
    if not worker.enabled(): start_job(id)

@app.post('/api/tests', status_code=202)
@serial_submission
async def create(request: Request, payload: str = Form(...), video: UploadFile | None = File(None)):
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
    media_digest = hashlib.sha256()
    try:
        if data.sourceType=='upload':
            suffix=Path(video.filename or '').suffix.lower()
            if suffix not in ('.mp4','.mov','.webm'): raise HTTPException(422,'Supported formats: MP4, MOV and WebM.')
            size=0
            with (directory/('source'+suffix)).open('wb') as f:
                while chunk := await video.read(1024*1024):
                    size+=len(chunk)
                    if size>int(os.getenv('MAX_UPLOAD_MB','100'))*1024*1024: raise HTTPException(413,'Video is too large.')
                    media_digest.update(chunk)
                    f.write(chunk)
            if not size: raise HTTPException(422,'Video is empty.')
        admitted = await asyncio.to_thread(budgets.admit, id, data.model_dump(), request.headers.get('idempotency-key'), media_digest.hexdigest())
        if admitted != id:
            shutil.rmtree(directory)
            return {'id': admitted}
        launch(id)
        return {'id':id}
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise
    finally:
        if video: await video.close()

@app.get('/api/tests/{id}')
def get(id: str):
    row=find(id)
    row['version']=cached(store.MEDIA/id,'experiment.json')
    return row

@app.post('/api/tests/{id}/retry')
@serial_submission
async def retry(id: str):
    row=find(id)
    if id in jobs: raise HTTPException(409,'Test is already running.')
    if len(jobs)>=2: raise HTTPException(429,'Two tests are already running.')
    if row['status'] not in ('failed','partial','interrupted','cancelled'): raise HTTPException(409,'Only failed, interrupted, cancelled or partial tests can be retried.')
    try: Provider('groq')
    except ProviderError as exc: raise HTTPException(422,str(exc))
    await asyncio.to_thread(budgets.charge, 'viewers', row['payload'].get('size',25))
    store.update(id,status='queued',error=None)
    launch(id)
    return {'id':id}

@app.post('/api/tests/{id}/cancel')
async def cancel(id: str):
    row=find(id)
    if row['status'] not in ('queued','running'):
        raise HTTPException(409, 'This simulation is not running.')
    store.update(id,status='cancelled',stage='Cancelled',error='Cancelled by you. Completed stages are retained for a later resume.')
    task = jobs.get(id)
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    return {'id':id, 'status':'cancelled'}

@app.delete('/api/tests/{id}')
async def delete(id: str):
    row=find(id)
    if id in jobs or id in chat_jobs or row['status'] in ('queued','running'):
        raise HTTPException(409,'Cancel the simulation and wait for active requests before deleting.')
    # Keep a retryable database record until private files are actually removed.
    store.update(id,status='deleting',stage='Deleting private files')
    try:
        directory=store.MEDIA/id
        if directory.exists(): await asyncio.to_thread(shutil.rmtree, directory)
        await asyncio.to_thread(store.delete, id)
    except Exception:
        raise HTTPException(503, 'Deletion is incomplete. Retry to finish removing the remaining data.') from None
    return {'deleted':True}

@app.get('/api/tests/{id}/frames/{name}')
def frame(id: str,name: str):
    find(id)
    import re
    if not re.fullmatch(r'frame-\d+\.jpg',name): raise HTTPException(404)
    path=store.MEDIA/id/name
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path,media_type='image/jpeg')

@app.get('/api/tests/{id}/export')
async def export(id: str):
    row=await asyncio.to_thread(find, id)
    row['version']=cached(store.MEDIA/id,'experiment.json')
    row['liveNetwork']=await live_test(id)
    return JSONResponse(row,headers={'Content-Disposition':f'attachment; filename="ripple-{id}.json"'})


@app.get('/api/tests/{id}/live')
async def live_test(id: str):
    row=await asyncio.to_thread(find, id)
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
def private_video(id: str):
    row=find(id)
    if row['payload']['sourceType']!='upload': raise HTTPException(404,'No uploaded video')
    paths=list((store.MEDIA/id).glob('source.*'))
    if not paths: raise HTTPException(404,'Video unavailable')
    path=paths[0]
    return FileResponse(path,media_type={'.mp4':'video/mp4','.mov':'video/quicktime','.webm':'video/webm'}.get(path.suffix,'application/octet-stream'))

@app.post('/api/tests/{id}/versions',status_code=202)
@serial_submission
async def experiment(id: str, payload: ExperimentInput):
    from .experiments import create_version
    row=find(id)
    if row['status'] not in ('completed','partial'): raise HTTPException(409,'Finish the original simulation first.')
    if id in jobs or len(jobs)>=2: raise HTTPException(429,'Wait for running simulations to finish.')
    try:
        Provider('groq')
        child=await asyncio.to_thread(create_version,row,payload)
    except (ValueError,ProviderError) as exc: raise HTTPException(422,str(exc))
    launch(child)
    return {'id':child}

@app.get('/api/tests/{id}/compare/{other}')
def comparison(id: str, other: str):
    from .experiments import compare
    try: return compare(find(id),find(other))
    except ValueError as exc: raise HTTPException(409,str(exc))

@app.get('/api/tests/{id}/versions')
def version_history(id: str):
    row=find(id)
    version=cached(store.MEDIA/id,'experiment.json') or {}
    root=version.get('rootId',id)
    versions=[]
    offset=0
    while True:
        candidates=store.listing(offset=offset)
        for candidate in candidates:
            metadata=cached(store.MEDIA/candidate['id'],'experiment.json') or {}
            if candidate['id']==root or metadata.get('rootId')==root:
                versions.append(dict(candidate,parentId=metadata.get('parentId')))
        if len(candidates)<100: break
        offset+=100
    return versions

@app.get('/api/tests/{id}/chat')
def conversation(id: str):
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
    try:
        provider = Provider('groq')
        await asyncio.to_thread(budgets.charge, 'chat', 1)
        return await answer(row,payload.message,provider,semaphore)
    except ProviderError as exc: raise HTTPException(502,str(exc))
    finally: chat_jobs.discard(id)

@app.get('/api/tests/{id}/report')
def report(id: str):
    from .reports import creator_report
    row=find(id)
    if not row.get('result'): raise HTTPException(409,'A report needs saved simulation results.')
    return Response(creator_report(row),media_type='text/markdown',headers={'Content-Disposition':f'attachment; filename="ripple-{id}-report.md"'})
