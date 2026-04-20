from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str = Field(description="사용자 ID")
    user_name: str = Field(description="사용자 이름")
    email: str = Field(description="이메일")
    department: str | None = Field(default=None, description="소속 부서")


class UserActivityResponse(BaseModel):
    """사용자 활동 이력 응답"""
    recent_projects: list["RecentProject"] = Field(default_factory=list)


class RecentProject(BaseModel):
    project_id: str
    project_name: str
    last_accessed_at: str


class UserSettingsResponse(BaseModel):
    """사용자 개인 설정 응답"""
    jira_pat: str | None = Field(default=None, description="Jira PAT (마스킹)")
    confluence_pat: str | None = Field(default=None, description="Confluence PAT (마스킹)")
    notification_enabled: bool = Field(default=True, description="알림 활성화 여부")


class UserSettingsUpdate(BaseModel):
    """사용자 개인 설정 수정"""
    jira_pat: str | None = Field(default=None, description="Jira PAT")
    confluence_pat: str | None = Field(default=None, description="Confluence PAT")
    notification_enabled: bool | None = Field(default=None, description="알림 활성화 여부")
