"""Run with the same venv as Ripple. Never prints API keys or uploaded content."""
import argparse
import asyncio
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')

def main():
    parser=argparse.ArgumentParser(description='Check Ripple configuration without printing secrets.')
    parser.add_argument('--groq',action='store_true',help='Also query the official Groq model list (no generation).')
    args=parser.parse_args()
    from app.providers import Provider,ProviderError,model_setting
    print('Ripple v3 setup check')
    from app.skills import SkillRegistry
    registry=SkillRegistry()
    print('Reviewed agent skills:', len(registry.skills))
    print('.env found:',(ROOT/'.env').exists())
    print('ffmpeg:',bool(shutil.which('ffmpeg')))
    print('ffprobe:',bool(shutil.which('ffprobe')))
    for name in ('groq','gemini'):
        key=os.getenv(name.upper()+'_API_KEY','').strip()
        print(name+' key:','present (hidden)' if key else 'missing')
        if key:
            try:
                provider=Provider(name)
                print(name+' text model:',provider.model)
                print(name+' vision model:',provider.vision)
            except ProviderError as exc: print('CONFIG ERROR:',str(exc))
    try: print('Transcription:',model_setting('GROQ_TRANSCRIPTION_MODEL','whisper-large-v3-turbo'))
    except ProviderError as exc: print('CONFIG ERROR:',str(exc))
    if args.groq:
        try:
            result=asyncio.run(Provider('groq').models())
            for role,model in result['configured'].items(): print(role+':',model,'LISTED' if model in result['models'] else 'NOT LISTED')
            print('Active model IDs:',', '.join(result['models']))
        except ProviderError as exc: print('GROQ ERROR:',str(exc))
        except Exception: print('GROQ ERROR: model discovery could not connect. Check connectivity.')

if __name__=='__main__': main()
