"""Discover only reviewed, repository-owned Agent Skills; never user-uploaded files."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parent.parent / 'skills'


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    source: str
    version: str
    role: str


class SkillRegistry:
    def __init__(self, root=ROOT):
        root = Path(root).resolve()
        self.skills = {}
        for path in sorted(root.glob('*/SKILL.md')):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('Skill files must stay inside the reviewed skill directory.')
            raw = path.read_text(encoding='utf-8')
            parts = raw.split('---', 2)
            if len(parts) != 3 or parts[0].strip():
                raise ValueError(f'Invalid skill frontmatter: {path.parent.name}')
            meta = yaml.safe_load(parts[1])
            if not isinstance(meta, dict):
                raise ValueError(f'Invalid skill frontmatter: {path.parent.name}')
            name = meta.get('name', '')
            description = meta.get('description', '')
            if (not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)
                    or len(name) > 64 or name != path.parent.name
                    or not isinstance(description, str) or not 0 < len(description) <= 1024
                    or not parts[2].strip()):
                raise ValueError(f'Invalid skill metadata: {path.parent.name}')
            role = meta.get('metadata', {}).get('role', '')
            if role not in ('persona', 'synthesis'):
                raise ValueError(f'Skill needs a persona or synthesis role: {name}')
            self.skills[name] = Skill(name, description, parts[2].strip(), raw,
                                     hashlib.sha256(raw.encode()).hexdigest()[:16], role)
        if not self.skills:
            raise ValueError('No reviewed agent skills found.')

    def catalog(self, role):
        return [dict(name=s.name, description=s.description, version=s.version)
                for s in self.skills.values() if s.role == role]

    def load(self, name, role):
        skill = self.skills.get(name)
        if not skill or skill.role != role:
            raise ValueError('Choose a skill from the available catalog.')
        return skill
