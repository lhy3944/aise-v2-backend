from pydantic import BaseModel, Field


class SkillDraft(BaseModel):
    name: str
    description: str = ""
    body: str
    source_type: str
    source_url: str | None = None
    source_ref: str | None = None
    content_hash: str
    preview: str


class SkillPreviewGithubRequest(BaseModel):
    url: str
    name: str | None = None
    description: str | None = None


class SkillPreviewTextRequest(BaseModel):
    body: str
    name: str | None = None
    description: str | None = None


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    body: str = Field(min_length=1)
    source_type: str
    source_url: str | None = None
    source_ref: str | None = None
    content_hash: str | None = None
    enabled: bool = True


class SkillUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    body: str
    source_type: str
    source_url: str | None = None
    source_ref: str | None = None
    content_hash: str
    enabled: bool
    created_at: str
    updated_at: str


class SkillListResponse(BaseModel):
    skills: list[SkillResponse] = Field(default_factory=list)
