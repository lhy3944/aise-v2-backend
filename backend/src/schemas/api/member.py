from pydantic import BaseModel, Field

from .common import MemberRole


class MemberInvite(BaseModel):
    """멤버 초대 요청"""
    email: str = Field(description="초대할 사용자 이메일")
    role: MemberRole = Field(description="부여할 역할")


class MemberRoleUpdate(BaseModel):
    """멤버 역할 변경 요청"""
    role: MemberRole = Field(description="변경할 역할")


class MemberResponse(BaseModel):
    """멤버 응답"""
    user_id: str = Field(description="사용자 ID")
    user_name: str = Field(description="사용자 이름")
    email: str = Field(description="이메일")
    role: MemberRole = Field(description="역할")


class MemberListResponse(BaseModel):
    """멤버 목록 응답"""
    members: list[MemberResponse] = Field(default_factory=list)
