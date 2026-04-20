from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class GlossaryCreate(BaseModel):
    """용어 추가 요청"""
    term: str = Field(description="��어")
    definition: str = Field(description="정의")
    product_group: str | None = Field(default=None, description="제품군")
    synonyms: list[str] = Field(default_factory=list, description="동의어")
    abbreviations: list[str] = Field(default_factory=list, description="약어")
    section_tags: list[str] = Field(default_factory=list, description="관련 섹션 태그")
    source_document_id: uuid.UUID | None = Field(default=None, description="출처 문서 ID")


class GlossaryUpdate(BaseModel):
    """용어 수정 요청"""
    term: str | None = Field(default=None)
    definition: str | None = Field(default=None)
    product_group: str | None = Field(default=None)
    synonyms: list[str] | None = Field(default=None)
    abbreviations: list[str] | None = Field(default=None)
    section_tags: list[str] | None = Field(default=None)


class GlossaryResponse(BaseModel):
    """용어 응답"""
    glossary_id: str = Field(description="용어 ID")
    term: str = Field(description="용어")
    definition: str = Field(description="정의")
    product_group: str | None = Field(default=None, description="제품군")
    synonyms: list[str] = Field(default_factory=list)
    abbreviations: list[str] = Field(default_factory=list)
    section_tags: list[str] = Field(default_factory=list)
    source_document_id: str | None = Field(default=None)
    source_document_name: str | None = Field(default=None)
    is_auto_extracted: bool = Field(default=False)
    is_approved: bool = Field(default=True)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class GlossaryListResponse(BaseModel):
    """용어 목록 응답"""
    glossary: list[GlossaryResponse] = Field(default_factory=list)


class GlossaryGenerateResponse(BaseModel):
    """Glossary 자동 생성 응답 (요구사항 기반 - 레거시)"""
    generated_glossary: list[GlossaryCreate] = Field(default_factory=list)


class GlossaryExtractedItem(BaseModel):
    """지식 문서에서 추출된 용어 후보"""
    term: str
    definition: str
    synonyms: list[str] = Field(default_factory=list)
    abbreviations: list[str] = Field(default_factory=list)
    source_document_id: str | None = None
    source_document_name: str | None = None


class GlossaryExtractResponse(BaseModel):
    """지식 문서 기반 용어 추출 응답"""
    candidates: list[GlossaryExtractedItem] = Field(default_factory=list)


class GlossaryApproveRequest(BaseModel):
    """추출된 용어 일괄 승인 요청"""
    items: list[GlossaryCreate] = Field(description="승인할 용어 목록")
