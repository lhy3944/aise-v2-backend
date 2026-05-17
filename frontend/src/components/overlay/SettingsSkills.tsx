'use client';

import {
  ClipboardType,
  Github,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  Upload,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { showToast } from '@/lib/toast';
import { cn } from '@/lib/utils';
import { skillService } from '@/services/skill-service';
import type { SkillDraft, SkillSourceType, UserSkill } from '@/types/skills';

const SOURCE_LABEL: Record<SkillSourceType, string> = {
  github: 'GitHub',
  upload: 'MD 파일',
  text: '직접 입력',
};

const SOURCE_ICON = {
  github: Github,
  upload: Upload,
  text: ClipboardType,
};

export function SettingsSkills() {
  const [skills, setSkills] = useState<UserSkill[]>([]);
  const [sourceType, setSourceType] = useState<SkillSourceType>('github');
  const [githubUrl, setGithubUrl] = useState('');
  const [textBody, setTextBody] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<SkillDraft | null>(null);
  const [draftName, setDraftName] = useState('');
  const [draftDescription, setDraftDescription] = useState('');
  const [draftEnabled, setDraftEnabled] = useState(true);
  const [loading, setLoading] = useState(false);

  const enabledCount = useMemo(
    () => skills.filter((skill) => skill.enabled).length,
    [skills],
  );

  async function refresh() {
    const response = await skillService.list();
    setSkills(response.skills);
  }

  useEffect(() => {
    refresh().catch(() => {
      showToast.error('스킬 목록을 불러오지 못했습니다.');
    });
  }, []);

  function applyDraft(nextDraft: SkillDraft) {
    setDraft(nextDraft);
    setDraftName(nextDraft.name);
    setDraftDescription(nextDraft.description);
    setDraftEnabled(true);
  }

  async function handlePreview() {
    setLoading(true);
    try {
      if (sourceType === 'github') {
        applyDraft(await skillService.previewGithub(githubUrl.trim()));
      } else if (sourceType === 'upload') {
        if (!selectedFile) {
          showToast.warning('Markdown 파일을 선택해주세요.');
          return;
        }
        applyDraft(await skillService.previewUpload(selectedFile));
      } else {
        applyDraft(await skillService.previewText(textBody, 'Custom Skill'));
      }
    } catch (error) {
      showToast.error(
        '스킬 미리보기에 실패했습니다.',
        error instanceof Error ? error.message : undefined,
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!draft) return;
    setLoading(true);
    try {
      await skillService.create({
        name: draftName.trim(),
        description: draftDescription.trim(),
        body: draft.body,
        source_type: draft.source_type,
        source_url: draft.source_url,
        source_ref: draft.source_ref,
        content_hash: draft.content_hash,
        enabled: draftEnabled,
      });
      setDraft(null);
      setGithubUrl('');
      setTextBody('');
      setSelectedFile(null);
      await refresh();
      showToast.success('스킬을 저장했습니다.');
    } catch (error) {
      showToast.error(
        '스킬 저장에 실패했습니다.',
        error instanceof Error ? error.message : undefined,
      );
    } finally {
      setLoading(false);
    }
  }

  async function toggleSkill(skill: UserSkill, enabled: boolean) {
    try {
      const updated = await skillService.update(skill.id, { enabled });
      setSkills((prev) => prev.map((item) => (item.id === skill.id ? updated : item)));
    } catch {
      showToast.error('스킬 상태를 변경하지 못했습니다.');
    }
  }

  async function deleteSkill(skill: UserSkill) {
    try {
      await skillService.delete(skill.id);
      setSkills((prev) => prev.filter((item) => item.id !== skill.id));
      showToast.success('스킬을 삭제했습니다.');
    } catch {
      showToast.error('스킬을 삭제하지 못했습니다.');
    }
  }

  return (
    <div className='flex w-full flex-col gap-6'>
      <section className='flex flex-col gap-4'>
        <div className='flex items-center justify-between gap-3'>
          <div>
            <h3 className='text-fg-primary text-sm font-semibold'>스킬 추가</h3>
            <p className='text-fg-muted mt-1 text-xs'>
              Markdown 기반 개인화 지침을 AI 응답과 산출물 생성에 적용합니다.
            </p>
          </div>
          <Button variant='outline' size='sm' onClick={refresh} disabled={loading}>
            <RefreshCw className='size-4' />
            새로고침
          </Button>
        </div>

        <Tabs
          value={sourceType}
          onValueChange={(value) => {
            setSourceType(value as SkillSourceType);
            setDraft(null);
          }}
        >
          <TabsList variant='line'>
            {(['github', 'upload', 'text'] as SkillSourceType[]).map((type) => {
              const Icon = SOURCE_ICON[type];
              return (
                <TabsTrigger key={type} value={type} className='gap-1.5'>
                  <Icon className='size-3.5' />
                  {SOURCE_LABEL[type]}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>

        {sourceType === 'github' && (
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='skill-github-url'>GitHub URL</Label>
            <Input
              id='skill-github-url'
              value={githubUrl}
              onChange={(event) => setGithubUrl(event.target.value)}
              placeholder='https://github.com/owner/repo/blob/main/path/SKILL.md'
            />
          </div>
        )}

        {sourceType === 'upload' && (
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='skill-md-file'>Markdown 파일</Label>
            <Input
              id='skill-md-file'
              type='file'
              accept='.md,text/markdown'
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </div>
        )}

        {sourceType === 'text' && (
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='skill-text'>Markdown</Label>
            <Textarea
              id='skill-text'
              value={textBody}
              onChange={(event) => setTextBody(event.target.value)}
              placeholder={
                '---\nname: my-style\ndescription: 선호하는 작업 방식\n---\n응답은 결론 먼저 작성합니다.'
              }
              className='min-h-36 resize-y'
            />
          </div>
        )}

        <div className='flex justify-end'>
          <Button onClick={handlePreview} disabled={loading}>
            <Plus className='size-4' />
            미리보기
          </Button>
        </div>
      </section>

      {draft && (
        <>
          <Separator />
          <section className='flex flex-col gap-4'>
            <div className='flex items-center justify-between gap-3'>
              <h3 className='text-fg-primary text-sm font-semibold'>미리보기</h3>
              <Badge variant='outline'>{SOURCE_LABEL[draft.source_type]}</Badge>
            </div>

            <div className='grid grid-cols-1 gap-3 sm:grid-cols-2'>
              <div className='flex flex-col gap-1.5'>
                <Label htmlFor='skill-draft-name'>이름</Label>
                <Input
                  id='skill-draft-name'
                  value={draftName}
                  onChange={(event) => setDraftName(event.target.value)}
                />
              </div>
              <div className='flex flex-col gap-1.5'>
                <Label htmlFor='skill-draft-description'>설명</Label>
                <Input
                  id='skill-draft-description'
                  value={draftDescription}
                  onChange={(event) => setDraftDescription(event.target.value)}
                />
              </div>
            </div>

            <div className='border-line-primary bg-canvas-secondary/40 rounded-md border p-3'>
              <p className='text-fg-secondary text-xs leading-relaxed'>{draft.preview}</p>
              {draft.source_ref && (
                <p className='text-fg-muted mt-2 truncate text-[11px]'>{draft.source_ref}</p>
              )}
            </div>

            <div className='flex items-center justify-between gap-3'>
              <div className='flex flex-col gap-0.5'>
                <Label htmlFor='skill-draft-enabled'>활성화</Label>
                <span className='text-fg-muted text-xs'>
                  저장 후 새 AI 요청부터 개인화 지침으로 적용됩니다.
                </span>
              </div>
              <Switch
                id='skill-draft-enabled'
                checked={draftEnabled}
                onCheckedChange={setDraftEnabled}
              />
            </div>

            <div className='flex justify-end'>
              <Button onClick={handleSave} disabled={loading || !draftName.trim()}>
                <Save className='size-4' />
                저장
              </Button>
            </div>
          </section>
        </>
      )}

      <Separator />

      <section className='flex flex-col gap-3'>
        <div className='flex items-center justify-between'>
          <h3 className='text-fg-primary text-sm font-semibold'>내 스킬</h3>
          <span className='text-fg-muted text-xs'>
            {enabledCount}/{skills.length} 활성
          </span>
        </div>

        {skills.length === 0 ? (
          <div className='border-line-primary rounded-md border border-dashed p-5 text-center'>
            <p className='text-fg-muted text-sm'>저장된 스킬이 없습니다.</p>
          </div>
        ) : (
          <div className='flex flex-col gap-2'>
            {skills.map((skill) => {
              const Icon = SOURCE_ICON[skill.source_type];
              return (
                <div
                  key={skill.id}
                  className={cn(
                    'border-line-primary flex items-start gap-3 rounded-md border p-3',
                    !skill.enabled && 'opacity-60',
                  )}
                >
                  <div className='bg-canvas-secondary text-fg-secondary rounded-md p-2'>
                    <Icon className='size-4' />
                  </div>
                  <div className='min-w-0 flex-1'>
                    <div className='flex flex-wrap items-center gap-2'>
                      <p className='text-fg-primary truncate text-sm font-medium'>
                        {skill.name}
                      </p>
                      <Badge variant='secondary' className='px-1.5 py-0 text-[10px]'>
                        {SOURCE_LABEL[skill.source_type]}
                      </Badge>
                    </div>
                    {skill.description && (
                      <p className='text-fg-secondary mt-1 line-clamp-2 text-xs leading-relaxed'>
                        {skill.description}
                      </p>
                    )}
                    <p className='text-fg-muted mt-1 line-clamp-2 text-xs leading-relaxed'>
                      {skill.body}
                    </p>
                  </div>
                  <div className='flex shrink-0 items-center gap-2'>
                    <Switch
                      checked={skill.enabled}
                      onCheckedChange={(checked) => toggleSkill(skill, checked)}
                      aria-label={`${skill.name} 활성화`}
                    />
                    <Button
                      variant='ghost'
                      size='icon-sm'
                      onClick={() => deleteSkill(skill)}
                      aria-label={`${skill.name} 삭제`}
                    >
                      <Trash2 className='size-4' />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
