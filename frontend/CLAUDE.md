# AISE+ 프로젝트 가이드

## 기술 스택

- **Framework:** Next.js 16 / React 19
- **Language:** TypeScript 5 (strict mode)
- **Styling:** Tailwind CSS v4 + shadcn/ui
- **State:** Zustand 5
- **Animation:** motion (Framer Motion v12)
- **Icons:** lucide-react
- **Overlay:** 자체 overlay-store + OverlayProvider 패턴

---

## 디렉토리 구조 & 배치 규칙

```
src/
├── app/                    # Next.js 라우팅 (route groups 사용)
│   ├── (main)/             # 랜딩 페이지
│   └── (agent)/            # 메인 앱 (chat, workflow)
├── components/
│   ├── ui/                 # shadcn 기본 컴포넌트 (수정 최소화)
│   │   └── ai-elements/    # AI 전용 커스텀 UI 컴포넌트
│   ├── providers/          # Context/Provider 래퍼 (StoreProvider, OverlayProvider 등)
│   ├── layout/             # 레이아웃 컴포넌트 (Header, LeftSidebar, RightPanel 등)
│   ├── chat/               # 채팅 도메인 컴포넌트
│   ├── overlay/            # Modal, Dialog, Dropdown 등 오버레이 컴포넌트
│   └── shared/             # 도메인 무관 공통 컴포넌트
├── stores/                 # Zustand 스토어
├── hooks/                  # 커스텀 훅
├── lib/                    # 유틸리티 (utils.ts, fonts.ts)
└── types/                  # 전역 타입 정의
```

**배치 원칙:**

- 오버레이(모달/다이얼로그/드롭다운)는 `components/overlay/`
- Provider 컴포넌트는 `components/providers/`
- 특정 도메인에서만 쓰이면 해당 도메인 폴더, 여러 곳에서 쓰이면 `shared/`

---

## 네이밍 컨벤션

| 대상              | 규칙                                        | 예시                                |
| ----------------- | ------------------------------------------- | ----------------------------------- |
| 컴포넌트 파일     | PascalCase                                  | `LeftSidebar.tsx`, `ChatArea.tsx`   |
| 스토어 파일       | kebab-case + `-store` 접미사                | `chat-store.ts`, `overlay-store.ts` |
| 훅 파일           | camelCase + `use` 접두사                    | `useOverlay.ts`, `useResize.ts`     |
| Props 인터페이스  | `{ComponentName}Props`                      | `ConfirmDialogProps`                |
| 이벤트 핸들러     | `handle{Event}` (내부), `on{Event}` (props) | `handleConfirm`, `onOpenChange`     |
| 상수 배열/객체    | UPPER_SNAKE_CASE (모듈 스코프)              | `BOTTOM_ICONS`, `PROMPT_CARDS`      |
| Zustand 스토어 훅 | `use{Domain}Store`                          | `usePanelStore`, `useChatStore`     |

---

## 컴포넌트 작성 패턴

### 기본 구조

```tsx
"use client"; // 클라이언트 컴포넌트는 반드시 최상단에

import { ... } from "외부라이브러리";
import { ... } from "@/components/...";
import { ... } from "@/stores/...";
import { cn } from "@/lib/utils";

interface ComponentNameProps {
  // props 명시적 정의
}

export function ComponentName({ prop1, prop2 }: ComponentNameProps) {
  // ...
}
```

- `"use client"` 는 인터랙션이 있는 컴포넌트에만 붙임
- **named export** 사용 (default export 사용하지 않음)
- Props 인터페이스는 컴포넌트 바로 위에 선언

### Import 순서

```tsx
// 1. 외부 라이브러리
import { useState } from 'react';
import { motion } from 'motion/react';

// 2. 내부 컴포넌트 (@/ 절대경로)
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/stores/chat-store';

// 3. 유틸리티 / 타입
import { cn } from '@/lib/utils';
import type { AlertOptions } from '@/stores/overlay-store';
```

- **항상 `@/` 절대경로** 사용 (같은 폴더 내 relative import 금지)
- TypeScript 전용 import는 `import type` 사용

---

## 스타일링 패턴

### 클래스 병합은 반드시 `cn()` 사용

```tsx
import { cn } from '@/lib/utils';

<div className={cn('base-class', isActive && 'active-class', className)} />;
```

### 디자인 토큰 (CSS 변수 → Tailwind 유틸리티)

shadcn 기본 컬러가 아닌 **AISE+ 전용 토큰**을 우선 사용:

| Tailwind 유틸리티     | 의미            |
| --------------------- | --------------- |
| `bg-canvas-primary`   | 메인 배경       |
| `bg-canvas-secondary` | 서브 배경       |
| `bg-canvas-surface`   | 카드/표면       |
| `text-fg-primary`     | 기본 텍스트     |
| `text-fg-secondary`   | 보조 텍스트     |
| `text-fg-muted`       | 비활성 텍스트   |
| `text-accent-primary` | 강조색 (violet) |
| `border-line-primary` | 기본 보더       |
| `text-icon-default`   | 아이콘 기본색   |
| `text-icon-active`    | 아이콘 활성색   |

### 조건부 스타일

```tsx
// 상태에 따라 클래스 분기
<div
  className={cn('flex h-full flex-col', isOpen ? 'w-[220px] gap-2 pl-3' : 'w-[60px] items-center')}
/>
```

### 컬러 톤 원칙

기본 톤은 **모던 블랙 & 화이트**. accent 컬러는 최소한으로 사용한다.

- **기본**: `border-line-primary`, `bg-canvas-surface`, `text-fg-primary/secondary/muted` — 카드, 테이블, 그리드 등 일반 컴포넌트는 뉴트럴 톤 유지
- **accent 허용**: 현재 활성 탭, 선택된 항목의 하이라이트, CTA 버튼 등 **사용자 시선을 끌어야 하는 곳**에만 사용
- **accent 금지**: 카드 테두리, 테이블 행, 컨테이너 wrapper 등 **구조적 요소**에 accent 컬러 사용 금지 — `border-accent-primary` 같은 클래스를 장식 목적으로 쓰지 않는다

```tsx
// GOOD: 뉴트럴 톤 카드
<div className='border-line-primary bg-canvas-surface rounded-lg border p-4'>

// GOOD: 선택 상태에만 accent
<button className={cn(
  'border px-3 py-2',
  isActive ? 'border-accent-primary text-accent-primary' : 'border-line-primary text-fg-secondary',
)}>

// BAD: 카드 기본 테두리에 accent
<div className='border-accent-primary rounded-lg border p-4'>
```

### 인터랙티브 카드 UI 패턴

채팅 내 질문지, 요구사항 카드 등 사용자 인터랙션이 있는 카드 컴포넌트는 다음 규칙을 따른다.

**카드 컨테이너:**

- 외곽: `bg-canvas-surface border-line-primary rounded-xl border` — 뉴트럴 톤 유지, accent 테두리 금지
- 헤더/푸터 구분: `border-line-primary border-b` / `border-t` 사용

**선택 가능한 항목 (옵션 버튼):**

- 배경은 항상 **투명** — `bg-accent-*` 사용 금지
- 선택 상태: `border-accent-primary text-fg-primary` (보더만 accent)
- 미선택 상태: `border-line-primary text-fg-secondary hover:bg-canvas-secondary`

```tsx
// GOOD: 선택 시 보더만 accent, 배경 투명
<button className={cn(
  'rounded-lg border px-3 py-2 text-sm',
  isSelected ? 'border-accent-primary text-fg-primary' : 'border-line-primary text-fg-secondary',
)}>

// BAD: 선택 시 배경색 사용
<button className={cn(
  'rounded-lg border px-3 py-2',
  isSelected ? 'border-accent-primary/30 bg-accent-primary/5' : '...',
)}>
```

**액션 버튼:**

- 카드 하단에 배치, **항상 오른쪽 정렬** (`flex justify-end`)
- 카드에 헤더/푸터가 있는 경우 `border-t` 영역에 배치

### 크기는 Tailwind 단위 사용

- 고정 크기: `size-4`, `h-9 w-9`, `w-[220px]`
- 아이콘: `className="h-5 w-5"` 또는 `className="size-4"`

---

## Zustand 스토어 패턴

```typescript
// stores/example-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ExampleState {
  // 상태 먼저 정의
  value: string;
  // 액션은 상태 뒤에
  setValue: (v: string) => void;
}

export const useExampleStore = create<ExampleState>()(
  persist(
    (set) => ({
      value: '',
      setValue: (v) => set({ value: v }),
    }),
    {
      name: 'aise-example', // localStorage key
      partialize: (s) => ({ value: s.value }), // 영속화할 필드만
    },
  ),
);
```

**컴포넌트에서 셀렉터 패턴으로 구독:**

```tsx
// 필요한 것만 구독 (전체 스토어 구독 금지)
const value = useExampleStore((s) => s.value);
const setValue = useExampleStore((s) => s.setValue);
```

---

## 오버레이 시스템

모달/다이얼로그/알림은 **직접 컴포넌트 마운트 대신 `useOverlay` hook** 사용:

```tsx
const overlay = useOverlay();

// Alert (단순 알림)
overlay.alert({
  type: 'success' | 'warning' | 'info' | 'error',
  title: '제목',
  description: '내용',
});

// Confirm (확인/취소)
overlay.confirm({
  title: '삭제하시겠습니까?',
  variant: 'destructive',
  onConfirm: () => handleDelete(),
});

// Modal (커스텀 컨텐츠)
overlay.modal({
  title: '편집',
  size: 'sm' | 'md' | 'lg' | 'xl', // 기본값: "md"
  content: <MyForm />,
  footer: <Button onClick={() => overlay.closeModal()}>저장</Button>,
});
```

**새 오버레이 컴포넌트 추가 시:**

1. `components/overlay/` 에 컴포넌트 작성
2. `stores/overlay-store.ts` 에 options 인터페이스 + 상태 추가
3. `components/providers/OverlayProvider.tsx` 에 렌더링 추가
4. `hooks/useOverlay.ts` 에 호출 메서드 노출

---

## 애니메이션 패턴

```tsx
import { motion, AnimatePresence } from "motion/react";

// 두 상태 전환 (레이아웃 전환 등) - AnimatePresence + key 사용
<AnimatePresence mode="popLayout">
  {isOpen ? (
    <motion.div
      key="expanded"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 220, opacity: 1, transition: { type: "spring", stiffness: 400, damping: 30 } }}
      exit={{ width: 0, opacity: 0, transition: { duration: 0.2, ease: "easeOut" } }}
    />
  ) : (
    <motion.div key="collapsed" /* ... */ />
  )}
</AnimatePresence>

// 단순 등장/퇴장
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0 }}
  transition={{ duration: 0.2 }}
/>
```

**주의:** width/height 애니메이션 시 단일 `motion.div`에서 width만 바꾸면 내부 콘텐츠가 즉시 교체되어 부자연스러움 → `AnimatePresence`로 두 레이아웃을 전환하는 방식 사용

---

## shadcn 컴포넌트 사용 규칙

### 사용 가능한 컴포넌트 (`components/ui/`)

`button`, `dialog`, `alert-dialog`, `drawer`, `sheet`, `dropdown-menu`, `tabs`, `tooltip`, `badge`, `label`, `input`, `textarea`, `select`, `input-group`, `skeleton`, `scroll-area`, `separator`, `switch`, `avatar`, `hover-card`, `command`, `spinner`, `text-animate`, `aurora-text`

### 커스터마이징 원칙

- `components/ui/` 파일은 **직접 수정 최소화** (shadcn CLI로 관리됨)
- 커스텀이 필요하면 `components/overlay/` 또는 도메인 폴더에서 래핑
- className prop으로 스타일 오버라이드 (cn() 활용)

### Tooltip은 반드시 TooltipProvider 안에서 사용

`TooltipProvider`가 root layout에 이미 있으므로 별도 추가 불필요.

### ScrollArea에 flex-1 사용 시

부모에 반드시 `flex` 클래스 필요 (height 계산 이슈).

---

## 반응형 처리

- **Mobile:** `< 768px` → 드로어(Drawer) 방식
- **Tablet:** `768px ~ 1023px`
- **Desktop:** `>= 1024px` → 멀티패널 레이아웃

```tsx
// Tailwind 반응형 유틸리티
className = 'max-md:hidden'; // 모바일에서 숨김
className = 'lg:block'; // 데스크탑에서만 표시
className = 'hidden lg:flex'; // 데스크탑에서만 flex
```

`useMediaQuery` 훅으로 JS 레벨 분기도 가능.

---

## 폼 검증 패턴 (react-hook-form + zod)

폼 검증이 필요한 컴포넌트는 **반드시** react-hook-form + zod 조합을 사용한다. HTML5 네이티브 검증(브라우저 tooltip)은 사용하지 않는다.

### 필수 규칙

- `<form>` 태그에 **`noValidate`** 추가 — 브라우저 기본 tooltip 비활성화
- `<input>`에 `required` 속성 대신 **zod 스키마**로 검증
- 에러 메시지는 필드 바로 아래에 `text-destructive text-xs`로 표시
- 에러 상태의 입력 필드는 `border-destructive` 클래스 추가

### 기본 구조

```tsx
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const schema = z.object({
  name: z.string().trim().min(1, '이름을 입력하세요'),
  email: z.string().email('올바른 이메일을 입력하세요').optional(),
});

type FormValues = z.infer<typeof schema>;

export function MyForm({ onSubmit }: { onSubmit: (data: FormValues) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <Input {...register('name')} className={cn(errors.name && 'border-destructive')} />
      {errors.name && <p className='text-destructive text-xs'>{errors.name.message}</p>}
    </form>
  );
}
```

### 배열/복합 필드

`setValue`로 직접 업데이트하고 `{ shouldValidate: true }` 옵션 전달:

```tsx
const { setValue, watch } = useForm<FormValues>({ ... });
const modules = watch('modules');

// 프리셋 버튼 클릭 시
onClick={() => setValue('modules', preset, { shouldValidate: true })}
```

---

## Modal + Form 패턴

Modal 안에 폼을 배치할 때, **액션 버튼은 반드시 Modal의 `footer` prop으로 분리**한다. 폼 콘텐츠가 길어져도 Header/Footer가 고정되고 가운데 영역만 스크롤된다.

### 필수 규칙

- 폼 컴포넌트는 **폼 필드만** 렌더링 (제출/취소 버튼 포함 금지)
- 액션 버튼은 별도 컴포넌트로 export하여 Modal `footer`에 배치
- HTML `form` 속성으로 `<form>` 바깥의 버튼을 폼에 연결

### 기본 구조

```tsx
// 1. 폼 ID 상수 정의
const FORM_ID = 'my-feature-form';

// 2. 폼 컴포넌트 — 필드만
export function MyForm({ onSubmit }: Props) {
  return (
    <form id={FORM_ID} onSubmit={handleSubmit(onSubmit)} noValidate>
      {/* 입력 필드들 */}
    </form>
  );
}

// 3. 액션 컴포넌트 — form 속성으로 연결
export function MyFormActions({ onCancel, isLoading }: ActionProps) {
  return (
    <div className='flex justify-end gap-2'>
      <Button variant='outline' onClick={onCancel}>
        취소
      </Button>
      <Button type='submit' form={FORM_ID} disabled={isLoading}>
        저장
      </Button>
    </div>
  );
}
```

### 페이지에서 사용

```tsx
<Modal title='제목' footer={<MyFormActions onCancel={close} isLoading={loading} />}>
  <MyForm onSubmit={handleSubmit} />
</Modal>
```

### Modal 레이아웃 구조 (참고)

```
┌─ DialogContent (max-h, flex flex-col) ──────┐
│ Header  — border-b, 고정                     │
│ Content — flex-1 overflow-y-auto, 스크롤 영역 │
│ Footer  — border-t, 고정                     │
└─────────────────────────────────────────────┘
```

---

## Effect 내 동기 setState 금지 (React 19)

React 19 strict mode에서 `useEffect` 본문 안에서 동기적으로 `setState`를 호출하면 cascading render 경고가 발생한다. 비동기 콜백(`.then`, `await` 이후) 안에서의 `setState`는 허용된다.

### 금지 패턴

```tsx
// BAD: effect 본문에서 동기 setState → cascading render 경고
useEffect(() => {
  setLoading(true); // ← 금지
  fetchData().then(() => setLoading(false)); // ← 이건 OK (비동기)
}, [id]);
```

### 허용 패턴

**1. props 변경에 따른 state 조정 → 렌더 중 조건부 setState**

```tsx
const prevIdRef = useRef(id);
if (prevIdRef.current !== id) {
  prevIdRef.current = id;
  setLoading(true); // 렌더 중 setState — React가 허용하는 패턴
}
```

**2. 외부 스토어 기반 → `useSyncExternalStore`**

```tsx
const showRef = useRef(false);
const listenerRef = useRef<(() => void) | null>(null);

const subscribe = useCallback((cb: () => void) => {
  listenerRef.current = cb;
  return () => { listenerRef.current = null; };
}, []);

useEffect(() => {
  // ref 변경 + listener 호출 (setState 아님)
  showRef.current = true;
  listenerRef.current?.();
}, [dep]);

return useSyncExternalStore(subscribe, () => showRef.current, () => false);
```

**3. 초기 상태로 충분한 경우 → `useState` initializer만 사용**

```tsx
const [loading] = useState(() => !!id && !cache[id]); // 초기값으로 해결
```

---

## 금지 사항

- `default export` 사용 금지 → named export 사용
- 상대경로 cross-folder import 금지 → `@/` 절대경로
- `className` 문자열 직접 연결 금지 → `cn()` 사용
- 인라인 스타일(`style={{}}`) 사용 금지 → Tailwind/CSS 변수
- 스토어 전체 구독 금지 → 셀렉터 패턴 사용
- `console.log` 코드 잔류 금지
- HTML5 네이티브 폼 검증 사용 금지 → react-hook-form + zod 사용
- Modal 안에 폼 + 액션 버튼 함께 배치 금지 → 액션은 `footer` prop으로 분리
- `useEffect` 본문 내 동기 `setState` 금지 → 렌더 중 조정 또는 `useSyncExternalStore` 사용
