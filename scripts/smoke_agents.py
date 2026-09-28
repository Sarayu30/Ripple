"""Optional live check. Uses synthetic content; makes real, billable provider calls."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.agent_runtime import evaluate_persona
from app.deep_analysis import recommend
from app.providers import Provider, ProviderError


async def run(provider_name, deep):
    provider = Provider(provider_name)
    persona = dict(personaName='Smoke-test designer', personaType='Skeptical industry expert',
                   background='Freelance designer', motivation='Reduce repetitive work',
                   skepticism='Needs visible proof', viewingContext='Watching during lunch')
    content = {'transcript':'Here is a reusable checklist for your next client pitch. Start with the problem, '
               'show one relevant project, and finish with the next step. Save this checklist.',
               'caption':'Three steps for a clearer pitch.', 'limitations':['Text-only synthetic smoke test'],
               'evidence':{'transcript':True,'caption':True}}
    analysis = {'summary':'A three-step pitch checklist with a save CTA.', 'limitations':['No visual evidence']}
    result, audit = await evaluate_persona(provider, persona, content, analysis)
    print(json.dumps({'persona':'completed', 'model':provider.model, 'skills':audit['skills'],
                      'tools':audit['tools'], 'action':result.likelyAction}), flush=True)
    if deep:
        data = {'analysis':analysis, 'metrics':{'hookScore':result.hookScore},
                'limitations':content['limitations'], 'feedback':[{'id':'0','cohort':'target',
                    'type':result.personaType,'objection':result.objection,'edit':result.recommendedEdit,
                    'understood':result.understood,'sentiment':result.sentiment}]}
        rec, deep_audit = await recommend(provider, data,
            emit=lambda event:print(json.dumps(event), flush=True))
        print(json.dumps({'deepAnalysis':'completed','edits':len(rec.topEdits),
                          'modelCalls':deep_audit['modelCalls'],'tools':deep_audit['tools']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', type=Path, default=Path(__file__).resolve().parents[1]/'.env')
    parser.add_argument('--provider', choices=['groq','gemini'], default='groq')
    parser.add_argument('--deep', action='store_true', help='Also run the Deep Agents coordinator and specialists.')
    args = parser.parse_args()
    load_dotenv(args.env)
    try:
        asyncio.run(run(args.provider, args.deep))
    except ProviderError as exc:
        print(json.dumps({'outcome':'failed', **exc.details()}))
        sys.exit(1)
