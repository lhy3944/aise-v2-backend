# Code Conventions

> 프론트엔드 코드 작성 시 따르는 규칙. 지속적으로 업데이트.

## 디렉토리 구조

```
src/
├── app/              # App Router (페이지, 레이아웃)
├── components/       # UI 컴포넌트
│   ├── ui/           # shadcn/ui 기반 원자 컴포넌트 (Button, Badge, Input 등)
│   ├── shared/       # 여러 도메인에서 공유하는 컴포넌트 (Logo, ThemeToggle)
│   ├── layout/       # 레이아웃 컴포넌트 (Header, Sidebar, Footer)
│   ├── overlay/      # 다이얼로그, 드롭다운 등 오버레이
│   ├── chat/         # 채팅 관련
│   ├── landing/      # 랜딩 페이지 전용
│   └── projects/     # 프로젝트 도메인 컴포넌트
├── constants/        # 도메인별 상수 (project.ts, requirement.ts 등)
├── hooks/            # 커스텀 훅 (useResize, useMediaQuery 등)
├── lib/              # 유틸리티 함수
│   ├── utils.ts      # cn() 등 범용 유틸
│   ├── format.ts     # 포맷팅 유틸 (formatDate 등)
│   ├── api.ts        # API 클라이언트
│   └── fonts.ts      # 폰트 설정
├── stores/           # Zustand 상태 관리 (도메인별 분리)
├── config/           # 네비게이션 등 앱 설정
└── types/            # TypeScript 타입 정의
```

## 파일 배치 규칙

| 종류 | 위치 | 예시 |
|------|------|------|
| 도메인 상수 (라벨, 색상 맵) | `src/constants/{domain}.ts` | `constants/project.ts` |
| 유틸리티 함수 (포맷, 변환) | `src/lib/{기능}.ts` | `lib/format.ts` |
| 커스텀 훅 | `src/hooks/use{Name}.ts` | `hooks/useResize.ts` |
| 상태 관리 | `src/stores/{domain}-store.ts` | `stores/project-store.ts` |
| 타입 정의 | `src/types/{domain}.ts` | `types/project.ts` |

### 판단 기준

- **2개 이상 컴포넌트에서 공유되는 상수** → `src/constants/`
- **2개 이상 컴포넌트에서 공유되는 유틸리티 함수** → `src/lib/`
- **1개 컴포넌트에서만 사용** → 해당 컴포넌트 파일 내 정의

## Import 순서

```typescript
// 1. 외부 라이브러리
import { Badge } from '@/components/ui/badge';
import type { Project } from '@/types/project';
import { Box, Clock } from 'lucide-react';
import Link from 'next/link';

// 2. 내부 상수/유틸
import { MODULE_COLORS, MODULE_LABELS } from '@/constants/project';
import { formatDate } from '@/lib/format';
```

## 네이밍

| 대상 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일 | PascalCase | `ProjectCard.tsx` |
| 상수 파일 | kebab-case 또는 도메인명 | `project.ts` |
| 유틸 파일 | camelCase 또는 기능명 | `format.ts` |
| 상수 변수 | UPPER_SNAKE_CASE | `MODULE_LABELS` |
| 함수 | camelCase | `formatDate()` |
| 커스텀 훅 | use + PascalCase | `useMediaQuery` |
| Store | 도메인-store | `project-store.ts` |
