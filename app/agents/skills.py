"""Read only the allowlisted, version-controlled skills used by each agent."""
from pathlib import Path
from functools import lru_cache
import hashlib

ROOT = Path(__file__).resolve().parents[2] / 'skills'
NAMES = ('video-analysis','audience-segmentation','viewer-evaluation','virality-analysis','creative-optimization','insight-synthesis')

@lru_cache(maxsize=10)
def instruction(name):
    if name not in NAMES:
        raise ValueError('Unknown agent skill')
    return (ROOT / name / 'SKILL.md').read_text(encoding='utf-8') + '\n'

def catalog():
    return [{'name':name,'sha256':hashlib.sha256(instruction(name).encode()).hexdigest()} for name in NAMES]
