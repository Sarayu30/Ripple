from ..simulation import cached, checkpoint
from ..media import extract, preview
from ..schemas import Analysis
from ..providers import ProviderError
from .skills import instruction

async def run(state, runtime):
    row=state["row"]; payload=row["payload"]; directory=runtime.directory
    provider=runtime.provider; semaphore=runtime.semaphore; event=runtime.event; live=runtime.live
    context = cached(directory,'context.json')
    if context is None:
        context = {'audience':payload['audience'],'angle':payload['angle'],'goal':payload['goal'],'platform':payload['platform'],'cta':payload['cta'],'caption':payload['caption'],'transcript':payload['transcript'],'limitations':[], 'evidence':{'caption':bool(payload['caption']),'transcript':bool(payload['transcript'])}}
        if payload['sourceType']=='upload':
            paths = list(directory.glob('source.*'))
            if not paths: raise ValueError('Uploaded video is missing.')
            metadata, audio = await extract(paths[0],directory)
            context['metadata'] = metadata
            context['evidence']['metadata'] = True
            if audio and not context['transcript']:
                try:
                    context['transcript'] = await provider.transcribe(audio)
                    context['evidence']['transcript'] = bool(context['transcript'].strip())
                except (ProviderError, KeyError, IndexError) as exc: context['limitations'].append('Audio transcription unavailable: '+str(exc))
            frame_notes = []
            frames = metadata['frames']
            # Batch at most three images to respect the documented Groq vision limit.
            for start in range(0,len(frames),3):
                batch = frames[start:start+3]
                try:
                    async with semaphore:
                        note = await provider.json(Analysis,instruction('video-analysis') + 'Analyze only these time-stamped sampled video frames and supplied speech. Describe visual evidence, captions and on-screen text. If pacing, scene changes or drop-off cannot be inferred, say uncertain. Never claim full-motion observation.', {'frames':batch,'transcript':context['transcript'],'duration':metadata['duration']},[directory/f['file'] for f in batch])
                    frame_notes.append(note.model_dump())
                except ProviderError as exc:
                    context['limitations'].append(f'Frame batch {start//3+1}: {exc}')
            context['frameObservations'] = frame_notes
            context['evidence']['vision'] = bool(frame_notes)
            context['limitations'].append('Visual analysis uses sparse sampled frames, not continuous motion. OCR/captions and scene boundaries may be incomplete; attention drop-off is a hypothesis.')
        else:
            context['source'] = await preview(payload['url'])
            context['evidence']['oembed'] = 'oEmbed' in context['source']['access']
            context['limitations'].append(context['source']['access'])
        if not context['evidence'].get('vision') and not context['transcript'] and not context['caption']:
            raise ValueError('Insufficient content evidence. Add the spoken transcript or caption, or upload a video with a working vision model. A URL and intended message alone cannot support content evaluation.')
        checkpoint(directory,'context.json',context)
    experiment=cached(directory,'experiment.json')
    if experiment:
        context['experiment']=experiment['changes']
        context['limitations']=list(dict.fromkeys(context['limitations']+['What-if edits are creator proposals, not observed changes to the source media.']))
        checkpoint(directory,'context.json',context)
    analysis = cached(directory,'analysis.json')
    if analysis is None:
        async with semaphore:
            a = await provider.json(Analysis,instruction('video-analysis') + 'Analyze this short-form content. Distinguish observed evidence from hypotheses. Mark unavailable visual details as unavailable. Infer no exact drop-off timestamp without evidence. Treat intended message as creator context, not observed comprehension.', context)
        analysis = a.model_dump()
        checkpoint(directory,'analysis.json',analysis)
    return {"context":context,"analysis":analysis}
