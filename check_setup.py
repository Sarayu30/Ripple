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
    parser.add_argument('--database',action='store_true',help='Check PostgreSQL connectivity without changing data or displaying credentials.')
    args=parser.parse_args()
    from app.providers import Provider,ProviderError,model_setting
    print('Ripple v2 setup check')
    print('.env found:',(ROOT/'.env').exists())
    print('ffmpeg:',bool(shutil.which('ffmpeg')))
    print('ffprobe:',bool(shutil.which('ffprobe')))
    print('PostgreSQL URL:', 'present (hidden)' if os.getenv('DATABASE_URL','').strip() else 'missing')
    if args.database:
        try:
            import psycopg
            from app import store
            with psycopg.connect(store.database_url(), **store.connection_options()) as connection:
                connection.execute('SELECT 1').fetchone()
            print('PostgreSQL: connected')
        except Exception:
            print('DATABASE ERROR: connection failed. Check DATABASE_URL, TLS settings, and database availability. Credentials hidden.')
            return 1
    key=os.getenv('GROQ_API_KEY','').strip()
    print('Groq key:','present (hidden)' if key else 'missing')
    if key:
        try:
            provider=Provider('groq')
            print('Groq text model:',provider.model)
            print('Groq vision model:',provider.vision)
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

if __name__=='__main__': raise SystemExit(main())
