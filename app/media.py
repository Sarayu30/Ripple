import asyncio
import ipaddress
import json
import os
import re
import shutil
from urllib.parse import urlparse, urlunparse
import httpx


def source_url(raw):
    try:
        u = urlparse(raw.strip())
        host = (u.hostname or '').lower()
        if u.scheme != 'https' or not host or u.username or u.password or u.port not in (None,443):
            raise ValueError()
        if '.' not in host or host.endswith(('.local','.internal','.localhost')) or host == 'localhost':
            raise ValueError()
        try:
            if not ipaddress.ip_address(host).is_global: raise ValueError()
        except ValueError as exc:
            if re.fullmatch(r'[0-9.:]+', host): raise ValueError('Private or invalid addresses are not supported.') from exc
        if not re.fullmatch(r'[a-z0-9.-]+', host): raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Use a public HTTPS video URL without credentials or custom ports.')
    def domain(d): return host == d or host.endswith('.'+d)
    platform = next((label for d,label in [('instagram.com','Instagram'),('tiktok.com','TikTok'),('youtube.com','YouTube Shorts'),('youtu.be','YouTube Shorts'),('linkedin.com','LinkedIn')] if domain(d)), 'Other')
    return {'url':urlunparse((u.scheme,u.netloc,u.path,u.params,u.query,'')), 'platform':platform, 'host':host, 'title':platform+' source', 'access':'URL and supplied context only; original media was not fetched.'}

async def preview(raw):
    result = source_url(raw)
    endpoint = {'YouTube Shorts':'https://www.youtube.com/oembed','TikTok':'https://www.tiktok.com/oembed'}.get(result['platform'])
    # Only fixed official endpoints. Never fetch arbitrary user URLs, redirects, HTML or thumbnails.
    if endpoint:
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                async with client.stream('GET', endpoint, params={'url':result['url'],'format':'json'}) as response:
                    response.raise_for_status()
                    data = b''
                    async for chunk in response.aiter_bytes():
                        data += chunk
                        if len(data)>131072: raise ValueError('Oversized oEmbed response')
                value = json.loads(data)
            result.update(title=str(value.get('title',result['title']))[:500], author=str(value.get('author_name',''))[:200], access='Official oEmbed metadata plus supplied context; video media was not fetched.')
        except (httpx.HTTPError, ValueError):
            result['warning'] = 'Official source preview unavailable. Supply a transcript/caption or upload your video.'
    return result

async def run(*args):
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError:
        raise ValueError('Install FFmpeg and ffprobe and add them to PATH, then restart.')
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=90)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise ValueError('Media processing exceeded 90 seconds.')
    if proc.returncode:
        raise ValueError('Video could not be decoded. Upload a valid MP4, MOV or WebM.')
    return out.decode(errors='replace')

async def extract(path, directory):
    probe = json.loads(await run('ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)))
    duration = float(probe.get('format',{}).get('duration',0))
    streams = probe.get('streams',[])
    video = next((s for s in streams if s.get('codec_type')=='video'), None)
    if not video or not 0 < duration <= int(os.getenv('MAX_DURATION_SECONDS','180')):
        raise ValueError('Upload a video between 0 and MAX_DURATION_SECONDS (default 180 seconds).')
    if video.get('width',0)*video.get('height',0)>3840*2160:
        raise ValueError('Maximum supported frame size is 4K.')
    times = sorted(set(round(min(t,max(0,duration-.1)),2) for t in [0,1,3,duration*.25,duration*.5,duration*.75,duration-.2]))
    frames = []
    for i,t in enumerate(times):
        target = directory / f'frame-{i}.jpg'
        await run('ffmpeg','-nostdin','-y','-v','error','-protocol_whitelist','file,pipe','-ss',str(t),'-i',str(path),'-frames:v','1','-vf','scale=640:-2','-threads','1',str(target))
        if target.exists() and target.stat().st_size: frames.append({'file':target.name,'seconds':t})
    audio = None
    if any(s.get('codec_type')=='audio' for s in streams):
        audio = directory / 'audio.wav'
        await run('ffmpeg','-nostdin','-y','-v','error','-protocol_whitelist','file,pipe','-i',str(path),'-vn','-ac','1','-ar','16000','-threads','1',str(audio))
    return {'duration':duration,'width':video['width'],'height':video['height'],'codec':video.get('codec_name'),'frames':frames,'hasAudio':bool(audio)}, audio
