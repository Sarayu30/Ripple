from typing import Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict

Score = Annotated[int, Field(ge=0, le=100)]
Text = Annotated[str, Field(max_length=3000)]

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class TestInput(Strict):
    title: str = Field(min_length=1, max_length=120)
    audience: str = Field(min_length=10, max_length=2000)
    goal: Literal['awareness','engagement','leads','conversions','product education','brand recall']
    angle: str = Field(min_length=5, max_length=3000)
    platform: Literal['Instagram','TikTok','YouTube Shorts','LinkedIn','Other']
    cta: str = Field(max_length=500)
    size: Literal[25,50,100,250] = 25
    sourceType: Literal['upload','link']
    url: str = Field(default='', max_length=2000)
    transcript: str = Field(default='', max_length=20000)
    caption: str = Field(default='', max_length=5000)
    seedReach: int = Field(default=1000, ge=10, le=10000000)
    contactsPerShare: int = Field(default=8, ge=1, le=100)
    provider: Literal['groq','gemini'] = 'groq'
    outsidePercent: int = Field(default=20, ge=0, le=50)
    outsideAudience: str = Field(default="", max_length=1500)
    consent: Literal[True]

class PersonaProfile(Strict):
    personaName: str = Field(min_length=1, max_length=100)
    personaType: str = Field(min_length=1, max_length=100)
    background: Text
    motivation: Text
    skepticism: Text
    viewingContext: Text

class Profiles(Strict):
    personas: list[PersonaProfile] = Field(min_length=1, max_length=10)

class Reaction(Strict):
    personaName: str
    personaType: str
    hookScore: Score
    retentionScore: Score
    clarityScore: Score
    relevanceScore: Score
    trustScore: Score
    shareIntent: Score
    saveIntent: Score
    commentIntent: Score
    clickIntent: Score
    conversionIntent: Score
    sentiment: Literal['positive','neutral','negative','mixed']
    likelyAction: Literal['scroll','watch','like','save','comment','click','share','follow']
    reaction: Text
    objection: Text
    recommendedEdit: Text
    understood: Text
    shareReason: Text
    confusion: Text
    emotion: Text
    wouldStop: bool
    wouldFinish: bool
    likeIntent: Score
    followIntent: Score

class Scene(Strict):
    timestamp: str
    description: Text

class Analysis(Strict):
    summary: Text
    hook: Text
    dropOff: Text
    comprehension: Text
    ctaStrength: Text
    visualClarity: Text
    pacing: Text
    productVisibility: Text
    onScreenText: list[str]
    captions: list[str]
    scenes: list[Scene]
    shareableMoment: Text
    limitations: list[str]

class Recommendations(Strict):
    topEdits: list[str] = Field(min_length=3, max_length=3)
    alternativeHook: Text
    caption: Text
    cta: Text
    cover: Text
    abVariants: list[str] = Field(min_length=2, max_length=4)
    keep: list[str] = Field(min_length=1, max_length=5)
