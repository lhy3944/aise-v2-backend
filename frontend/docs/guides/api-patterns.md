# API Patterns

> API 연동 표준 패턴. 지속적으로 업데이트.

## 아키텍처

```
컴포넌트 (페이지)
  → useFetch / useMutation (데이터 페칭/변경 훅)
    → services/{domain}-service.ts (도메인별 API 호출)
      → lib/api.ts (HTTP 클라이언트, 공통 에러 처리)
        → Backend API
```

## API 클라이언트 (`lib/api.ts`)

```tsx
import { api, ApiError } from '@/lib/api';

// 기본 CRUD
const data = await api.get<ProjectListResponse>('/api/v1/projects');
const project = await api.post<Project>('/api/v1/projects', body);
const updated = await api.put<Project>('/api/v1/projects/123', body);
await api.delete<void>('/api/v1/projects/123');

// 글로벌 에러 처리 건너뛰기 (호출자가 직접 처리)
const data = await api.get('/path', { skipErrorHandling: true });
```

### 글로벌 에러 처리 (자동)

| 상태 코드 | 동작 |
|-----------|------|
| 401 | `/login`으로 리다이렉트 |
| 500+ | 에러 토스트 자동 표시 |
| 기타 | ApiError throw (호출자가 처리) |

## Service 레이어 (`services/`)

도메인별로 API 호출을 그룹화한다. 컴포넌트에서 직접 `api.get()`을 호출하지 않는다.

```tsx
// services/project-service.ts
import { api } from '@/lib/api';

export const projectService = {
  list: () => api.get<ProjectListResponse>('/api/v1/projects'),
  get: (id: string) => api.get<Project>(`/api/v1/projects/${id}`),
  create: (data: ProjectCreate) => api.post<Project>('/api/v1/projects', data),
  update: (id: string, data: ProjectUpdate) => api.put<Project>(`/api/v1/projects/${id}`, data),
  delete: (id: string) => api.delete<void>(`/api/v1/projects/${id}`),
};
```

## 데이터 페칭 (`useFetch`)

SWR 기반 GET 요청. 자동 캐싱, 재검증, 에러 재시도를 제공한다.

```tsx
import { useFetch } from '@/hooks/useFetch';

function ProjectList() {
  const { data, error, isLoading } = useFetch<ProjectListResponse>('/api/v1/projects');

  if (isLoading) return <Skeleton />;
  if (error) return <EmptyState title='로드 실패' description={error.message} />;
  if (!data?.projects.length) return <EmptyState title='프로젝트가 없습니다' />;

  return data.projects.map((p) => <ProjectCard key={p.project_id} project={p} />);
}
```

### 조건부 페칭

```tsx
// projectId가 있을 때만 요청
const { data } = useFetch<Project>(projectId ? `/api/v1/projects/${projectId}` : null);
```

### 수동 재검증

```tsx
const { data, mutate } = useFetch<ProjectListResponse>('/api/v1/projects');

// 삭제 후 목록 갱신
async function handleDelete(id: string) {
  await projectService.delete(id);
  mutate(); // 목록 다시 가져오기
}
```

## Mutation (`useMutation`)

POST/PUT/DELETE 요청. 로딩 상태, 에러 처리, 성공 토스트를 자동 관리한다.

```tsx
import { useMutation } from '@/hooks/useMutation';

function CreateProjectForm() {
  const { mutate: createProject, isLoading } = useMutation({
    mutationFn: (data: ProjectCreate) => projectService.create(data),
    successMessage: '프로젝트가 생성되었습니다',
    onSuccess: () => router.push('/projects'),
  });

  async function onSubmit(values: ProjectCreate) {
    await createProject(values);
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* ... */}
      <Button disabled={isLoading}>
        {isLoading ? '생성 중...' : '프로젝트 생성'}
      </Button>
    </form>
  );
}
```

### 에러 토스트 커스터마이징

```tsx
// 기본: error.message가 토스트에 표시
useMutation({ mutationFn: ... });

// 커스텀 에러 메시지
useMutation({ mutationFn: ..., errorMessage: '삭제할 수 없습니다' });

// 에러 토스트 비활성화 (직접 처리)
useMutation({ mutationFn: ..., errorMessage: false, onError: (err) => { /* ... */ } });
```

## 표준 로딩/에러/빈 상태 패턴

```tsx
function DataPage() {
  const { data, error, isLoading } = useFetch<Response>(key);

  // 1. 로딩
  if (isLoading) return <Skeleton />;

  // 2. 에러
  if (error) return <EmptyState title='데이터를 불러올 수 없습니다' description={error.message} />;

  // 3. 빈 상태
  if (!data?.items.length) {
    return (
      <EmptyState
        icon={FileX}
        title='항목이 없습니다'
        description='새 항목을 추가해보세요'
        action={<Button>추가</Button>}
      />
    );
  }

  // 4. 데이터 렌더링
  return <List items={data.items} />;
}
```
