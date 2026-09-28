"""Bounded, resumable, isolated persona agents with model-selected tools."""
import hashlib
import json
import os

from .providers import ProviderError
from .schemas import AgentDecision, Reaction
from .skills import SkillRegistry

VERSION = 'skills-v1'
TOOLS = [
    {'name': 'load_skill', 'argument': 'skill name',
     'description': 'Load the complete workflow of a persona skill from the catalog.'},
    {'name': 'inspect_evidence', 'argument': 'transcript | caption | analysis | limitations',
     'description': 'Read one source from this content. Never returns another persona response.'},
    {'name': 'finish', 'argument': '',
     'description': 'Ready to submit a structured reaction after loading a skill and inspecting evidence.'},
]


async def evaluate_persona(provider, persona, content, analysis, *, state=None,
                           save=lambda value: None, emit=lambda value: None, registry=None):
    registry = registry or SkillRegistry()
    catalog = registry.catalog('persona')
    fingerprint = hashlib.sha256(json.dumps(
        [VERSION, persona, content, analysis, catalog, provider.model], sort_keys=True
    ).encode()).hexdigest()
    if not state or state.get('fingerprint') != fingerprint:
        state = {'fingerprint': fingerprint, 'runtime': VERSION, 'phase': 'tools',
                 'steps': [], 'skills': [], 'evidence': [], 'observations': []}
        save(state)
    if state.get('reaction'):
        return Reaction.model_validate(state['reaction']), audit(state)
    sources = {'transcript': content.get('transcript', ''), 'caption': content.get('caption', ''),
               'analysis': analysis, 'limitations': content.get('limitations', [])}
    maximum = max(2, min(8, int(os.getenv('AGENT_MAX_TOOL_STEPS', '4'))))
    while state['phase'] == 'tools' and len(state['steps']) < maximum:
        workflows = '\n'.join(registry.load(s['name'], 'persona').instructions for s in state['skills'])
        decision = await provider.json(AgentDecision,
            'You are an independent audience agent. Choose your next tool, using the exact catalog names. '
            'A skill in loadedSkills is already active: do not load it again. '
            'Load the most relevant skill, inspect content evidence, then finish. '
            'Use your profile to choose additional checks if useful. Never request other viewers or external tools. '
            'The argument is one exact skill name or evidence source, or empty for finish. '
            '\nReviewed workflows already loaded:\n' + workflows,
            {'persona': persona, 'availableSkills': catalog, 'tools': TOOLS,
             'availableEvidence': list(sources), 'observations': state['observations'],
             'loadedSkills': state['skills'], 'remainingSteps': maximum-len(state['steps'])})
        step = {'tool': decision.tool, 'argument': decision.argument, 'status': 'completed'}
        observation = None
        try:
            if decision.tool == 'load_skill':
                skill = registry.load(decision.argument, 'persona')
                if skill.name not in [s['name'] for s in state['skills']]:
                    state['skills'].append({'name': skill.name, 'version': skill.version})
                observation = skill.instructions
            elif decision.tool == 'inspect_evidence':
                if decision.argument not in sources:
                    raise ValueError('Choose transcript, caption, analysis, or limitations.')
                if decision.argument not in state['evidence']:
                    state['evidence'].append(decision.argument)
                observation = sources[decision.argument] or 'No evidence available in this source.'
            elif state['skills'] and set(state['evidence']) & {'transcript', 'caption', 'analysis'}:
                state['phase'] = 'reaction'
            else:
                raise ValueError('Load a skill and inspect transcript, caption, or analysis before finishing.')
        except ValueError as exc:
            step['status'] = 'rejected'
            observation = str(exc)
        state['steps'].append(step)
        if observation is not None:
            state['observations'].append({'tool': decision.tool, 'argument': decision.argument,
                                          'result': observation})
        save(state)
        emit({'kind': 'agent_tool', **step,
              'message': f'{persona["personaName"]} · {decision.tool} {decision.argument} · {step["status"]}'})
    if not state['skills'] or not set(state['evidence']) & {'transcript', 'caption', 'analysis'}:
        # Reset just invalid planning on an explicit retry; never fabricate a successful tool call.
        state['fingerprint'] = None
        save(state)
        raise ProviderError('Agent exhausted its tool budget before loading a skill and reading evidence. Resume to retry.',
                            code='agent_budget', model=provider.model)
    state['phase'] = 'reaction'
    save(state)
    instructions = '\n\n'.join(registry.load(s['name'], 'persona').instructions for s in state['skills'])
    result = await provider.json(Reaction,
        'Evaluate the content independently as the supplied viewer using these reviewed skill instructions:\n'
        + instructions + '\nReturn subjective scores and stated intent, not measured probabilities. '
        'Cohort labels do not prescribe sentiment. You have no access to other viewers. '
        'Only source evidence supports observations; intended message is creator context.',
        {'persona': persona, 'content': content, 'analysis': analysis,
         'toolObservations': state['observations']})
    state['reaction'] = result.model_dump()
    state['phase'] = 'complete'
    save(state)
    return result, audit(state)


def audit(state):
    """Only observable actions and skill versions, never private deliberation."""
    return {'runtime': VERSION, 'skills': state['skills'], 'tools': state['steps'],
            'evidenceSources': state['evidence'], 'toolSteps': len(state['steps'])}
