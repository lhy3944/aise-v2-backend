from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """알림 응답"""
    notification_id: str = Field(description="알림 ID")
    type: str = Field(description="알림 유형 (review_request | invite | version_change)")
    message: str = Field(description="알림 메시지")
    project_id: str | None = Field(default=None, description="관련 프로젝트 ID")
    is_read: bool = Field(default=False, description="읽음 여부")
    created_at: str = Field(description="생성 일시")


class NotificationListResponse(BaseModel):
    """알림 목록 응답"""
    notifications: list[NotificationResponse] = Field(default_factory=list)
    unread_count: int = Field(default=0, description="미읽은 알림 수")
