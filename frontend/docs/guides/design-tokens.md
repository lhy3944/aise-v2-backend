# Design Tokens

> AISE+ 디자인 토큰 체계. `globals.css`에 정의된 CSS 변수 기반. 지속적으로 업데이트.

## 토큰 2레이어 구조

```
[shadcn 레이어]  --primary, --muted, --destructive ...
                  → shadcn/ui 컴포넌트가 사용 (Button, Input, Dialog 등)
                  → globals.css :root / .dark 에서 AISE+ 색상으로 매핑

[AISE+ 레이어]   --text-primary, --accent-primary, --border-primary ...
                  → 커스텀 컴포넌트가 사용 (ProjectCard, Header 등)
                  → Tailwind @theme에서 --color-fg-primary 등으로 연결
```

### 토큰 선택 가이드

| 상황 | 사용할 토큰 |
|------|------------|
| shadcn/ui 컴포넌트 내부 수정 | shadcn 토큰 (`bg-primary`, `text-muted-foreground`) |
| 커스텀 컴포넌트 작성 | AISE+ 토큰 (`text-fg-primary`, `bg-canvas-primary`) |
| 상태별 구분 색상 (모듈, 타입) | Tailwind 색상 허용 (`text-blue-600`, `bg-emerald-500/10`) |
| 랜딩/마케팅 장식 효과 | Tailwind 색상 허용 |
| 테마 프리뷰 미니어처 | 하드코딩 허용 (고정된 light/dark 미리보기) |

## AISE+ 시맨틱 토큰

### 배경 (Canvas)

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `bg-canvas-primary` | 페이지 배경 | `#FFFFFF` | `#0D0D0D` |
| `bg-canvas-secondary` | 섹션 배경 | `#F5F5F5` | `#161616` |
| `bg-canvas-surface` | 표면 (카드 내부 등) | `#EBEBEB` | `#1E1E1E` |
| `bg-canvas-input` | 입력 필드 배경 | `#F0F0F0` | `#2A2A2A` |
| `bg-card` | 카드 배경 (shadcn) | `#F3F3F6` | `#161616` |

### 텍스트 (Foreground)

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `text-fg-primary` | 주요 텍스트 | `#111111` | `#FFFFFF` |
| `text-fg-secondary` | 보조 텍스트 | `#666666` | `#999999` |
| `text-fg-muted` | 비활성/힌트 텍스트 | `#AAAAAA` | `#555555` |

### 테두리 (Line)

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `border-line-primary` | 기본 구분선 | `#E0E0E0` | `#333333` |
| `border-line-subtle` | 미묘한 구분선 | `#EEEEEE` | `#222222` |

### 강조 (Accent)

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `text-accent-primary` | 강조 텍스트, 링크 | `#5B5FC7` | `#4ECDC4` |
| `bg-accent-primary/10` | 강조 배경 (투명도) | - | - |

### 아이콘

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `text-icon-default` | 기본 아이콘 | `#777777` | `#888888` |
| `text-icon-active` | 활성 아이콘 | `#111111` | `#FFFFFF` |

### 레이아웃

| Tailwind 클래스 | 용도 | Light | Dark |
|-----------------|------|-------|------|
| `bg-sidebar-bg` | 사이드바 배경 | `#FAFAFA` | `#111111` |
| `bg-tab-active-bg` | 활성 탭 배경 | `#FFFFFF` | `#1E1E1E` |

## 사용 규칙

1. **시맨틱 토큰 우선** — `text-gray-500` 대신 `text-fg-secondary`
2. **하드코딩 금지** — `#5B5FC7` 대신 `text-accent-primary`
3. **다크모드 자동 대응** — 시맨틱 토큰은 `dark:` prefix 불필요
4. **shadcn 컴포넌트는 건드리지 않기** — shadcn 토큰이 globals.css에서 올바르게 매핑됨

## 허용되는 하드코딩 예외

| 케이스 | 이유 |
|--------|------|
| 모듈/타입 구분 색상 (blue, purple, emerald) | 시맨틱 의미가 있는 고정 색상 |
| 오버레이 배경 (`bg-black/50`) | shadcn 표준 패턴 |
| `text-white` on 강조 버튼 | 고대비 보장 |
| 테마 프리뷰 미니어처 | 테마와 무관하게 고정 표시 |
| 랜딩 페이지 장식 효과 | 브랜딩/마케팅 용도 |

## 타이포그래피

- 폰트: Inter + Pretendard (한글 fallback)
- body 기본: `text-fg-primary`, antialiased
- OpenType features: `cv02`, `cv03`, `cv04`, `cv11`

## 간격/라운딩

- radius 기본: `0.5rem` (`--radius`)
- shadcn radius 체계: `rounded-sm` ~ `rounded-4xl`
