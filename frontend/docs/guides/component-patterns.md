# Component Patterns

> 컴포넌트 설계 시 따르는 패턴과 규칙. 지속적으로 업데이트.

## 컴포넌트 분류

| 분류 | 위치 | 설명 | 예시 |
|------|------|------|------|
| 원자 (UI) | `components/ui/` | shadcn/ui 기반, 도메인 무관 | Button, Badge, Input |
| 공유 | `components/shared/` | 여러 도메인에서 재사용 | Logo, ThemeToggle |
| 레이아웃 | `components/layout/` | 페이지 골격 | Header, Sidebar |
| 오버레이 | `components/overlay/` | 모달, 다이얼로그, 드롭다운 | ConfirmDialog, SearchDialog |
| 도메인 | `components/{domain}/` | 특정 도메인 전용 | ProjectCard, RequirementItem |

## Link 내부 인터랙티브 요소 패턴

`<Link>` 안에 버튼(삭제, 즐겨찾기 등)을 넣으면 클릭 시 네비게이션이 트리거된다.
`NextTopLoader`도 `<a>` 클릭을 감지하므로 `preventDefault`로는 로더를 막을 수 없다.

### 해결: 형제 배치 패턴

```tsx
// Link 바깥에 버튼을 형제로 배치, absolute로 오버레이
<div className='group relative'>
  <Link href={href} className='block ...'>
    {/* 카드 내용 */}
  </Link>

  {onAction && (
    <button
      className='absolute top-3 right-3 ...'
      onClick={() => onAction(id)}
    >
      <Icon />
    </button>
  )}
</div>
```

- `<Link>`와 버튼이 DOM 상 분리되므로 이벤트 간섭 없음
- `group` + `group-hover:`로 hover 효과 공유
- `NextTopLoader`는 카드 클릭 시에만 정상 동작

## 높이 일관성 패턴

카드 리스트에서 선택적 콘텐츠(description 등) 유무에 따라 높이가 달라지는 문제.

```tsx
// 조건부 렌더링 대신 항상 렌더링 + min-height
<p className='mb-3 line-clamp-2 min-h-[2lh] text-sm text-fg-secondary'>
  {project.description}
</p>
```

- `min-h-[2lh]` — `line-clamp-2`의 2줄 높이를 항상 확보
- `lh` 단위는 해당 요소의 line-height 기준이라 font-size 변경에도 자동 대응

## 카드 vs 리스트 아이템

같은 데이터를 카드/리스트 두 가지 뷰로 보여줄 때:

| | ProjectCard | ProjectListItem |
|---|---|---|
| 레이아웃 | 세로 (block) | 가로 (flex row) |
| 설명 | 2줄 표시 (line-clamp-2) | 1줄 말줄임 (truncate) |
| 메타정보 위치 | 카드 하단 | 우측 정렬 |
| 반응형 | 그리드 열 수 조정 | 요소 숨김 (sm:flex, lg:flex) |

공통 상수/유틸은 `@/constants/`, `@/lib/`에서 import하여 중복 방지.

## Toast 사용 패턴

`sonner` 기반 Toast 시스템. 직접 `toast()` 대신 `showToast` 헬퍼를 사용한다.

```tsx
import { showToast } from '@/lib/toast';

// 기본 사용
showToast.success('저장되었습니다');
showToast.error('저장에 실패했습니다');
showToast.info('처리 중입니다');
showToast.warning('주의가 필요합니다');

// 비동기 작업 (로딩 → 성공/실패 자동 전환)
showToast.promise(saveProject(data), {
  loading: '저장 중...',
  success: '프로젝트가 저장되었습니다',
  error: '저장에 실패했습니다',
});
```

## 폼 패턴

`react-hook-form` + `zod` + `@/components/ui/form` 조합을 표준으로 사용한다.

```tsx
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';

const schema = z.object({
  name: z.string().min(1, '이름을 입력해주세요'),
  email: z.string().email('올바른 이메일을 입력해주세요'),
});

type FormValues = z.infer<typeof schema>;

function MyForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '' },
  });

  function onSubmit(values: FormValues) {
    // ...
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className='space-y-4'>
        <FormField
          control={form.control}
          name='name'
          render={({ field }) => (
            <FormItem>
              <FormLabel>이름</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}
```

## 테이블 패턴

`@/components/ui/table` 기반. 빈 상태는 `EmptyState` 컴포넌트를 사용한다.

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/shared/EmptyState';
import { FileX } from 'lucide-react';

function DataTable({ items }) {
  if (items.length === 0) {
    return <EmptyState icon={FileX} title='데이터가 없습니다' description='항목을 추가해주세요' />;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>이름</TableHead>
          <TableHead>상태</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.id}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.status}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```
