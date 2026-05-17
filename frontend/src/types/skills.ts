export type SkillSourceType = 'github' | 'upload' | 'text';

export interface SkillDraft {
  name: string;
  description: string;
  body: string;
  source_type: SkillSourceType;
  source_url?: string | null;
  source_ref?: string | null;
  content_hash: string;
  preview: string;
}

export interface UserSkill {
  id: string;
  name: string;
  description: string;
  body: string;
  source_type: SkillSourceType;
  source_url?: string | null;
  source_ref?: string | null;
  content_hash: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillListResponse {
  skills: UserSkill[];
}

export interface SkillCreateRequest {
  name: string;
  description: string;
  body: string;
  source_type: SkillSourceType;
  source_url?: string | null;
  source_ref?: string | null;
  content_hash?: string | null;
  enabled: boolean;
}
