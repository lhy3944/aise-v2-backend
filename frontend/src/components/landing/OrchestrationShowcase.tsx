'use client';

import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Button } from '../ui/button';

// === 데이터 모델 정의 ===
type OrchestrationMode = 'requirements' | 'design' | 'testing';

interface ModeDetails {
  id: OrchestrationMode;
  title: string;
  description: string;
  badges: string[];
}

const MODES: ModeDetails[] = [
  {
    id: 'requirements',
    title: 'Requirements & SRS',
    description:
      '자연어로 요구사항을 입력하면 AI가 구조화하고, Review를 거쳐 고품질 SRS를 생성합니다.',
    badges: ['요구사항 정제', 'AI Review', 'SRS 자동 생성'],
  },
  {
    id: 'design',
    title: 'Design & SAD',
    description:
      '요구사항 기반으로 Use Case, Interaction Diagram, 논리/물리 모델을 자동 설계합니다.',
    badges: ['Use Case Diagram', 'System Architecture', 'SAD 생성'],
  },
  {
    id: 'testing',
    title: 'Test Case Generation',
    description: '요구사항과 설계를 기반으로 테스트 케이스를 자동 생성하고 추적성을 관리합니다.',
    badges: ['요구사항 기반 TC', '독립모드 TC', '추적성 매트릭스'],
  },
];

// === SVG 네트워크 그래프용 점 좌표 정의 (뷰박스 400x400 기준 중앙=200,200) ===
const CENTER_NODE = { x: 200, y: 200, label: 'AISE' };

const NODES = {
  requirements: { x: 200, y: 50, label: 'Requirements' },
  srs: { x: 70, y: 130, label: 'SRS' },
  design: { x: 330, y: 130, label: 'Design' },
  sad: { x: 60, y: 270, label: 'SAD' },
  testcase: { x: 340, y: 270, label: 'Testcase' },
  review: { x: 200, y: 350, label: 'AI Review' },
};

export interface OrchestrationShowcaseProps {
  /** 자동으로 모드가 순환할지 여부 */
  autoPlay?: boolean;
  /** 자동 순환 간격 (밀리초 단위, 기본값 5000ms) */
  interval?: number;
}

export function OrchestrationShowcase({
  autoPlay = false,
  interval = 5000,
}: OrchestrationShowcaseProps) {
  const [activeMode, setActiveMode] = useState<OrchestrationMode>('requirements');

  useEffect(() => {
    if (!autoPlay) return;

    const timer = setInterval(() => {
      setActiveMode((current) => {
        const currentIndex = MODES.findIndex((m) => m.id === current);
        const nextIndex = (currentIndex + 1) % MODES.length;
        return MODES[nextIndex].id;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [autoPlay, interval, activeMode]);

  const activeModeData = MODES.find((m) => m.id === activeMode) || MODES[0];

  return (
    <section className='bg-canvas-primary text-fg-primary w-full px-4 py-16 transition-colors duration-300'>
      <div className='mx-auto flex max-w-6xl flex-col items-center justify-between gap-12 lg:flex-row lg:gap-24'>
        {/* === 좌측: SVG 애니메이션 영역 === */}
        <div className='relative flex w-full max-w-md items-center justify-center lg:w-1/2'>
          {/* 중앙 강조 글로우 이펙트 (동적 색상 및 펄스 적용) */}
          <motion.div
            animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className={`pointer-events-none absolute top-1/2 left-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl transition-colors duration-500 ${activeMode === 'requirements' ? 'bg-blue-500/20 dark:bg-blue-500/30' : ''} ${activeMode === 'design' ? 'bg-teal-500/20 dark:bg-teal-500/30' : ''} ${activeMode === 'testing' ? 'bg-purple-500/20 dark:bg-purple-500/30' : ''} `}
          />

          <svg viewBox='0 0 400 400' className='h-auto w-full max-w-[400px] overflow-visible'>
            <defs>
              <filter id='glow' x='-50%' y='-50%' width='200%' height='200%'>
                <feGaussianBlur stdDeviation='4' result='blur' />
                <feComposite in='SourceGraphic' in2='blur' operator='over' />
              </filter>
            </defs>

            {/* 1. 연결 선 (Edges) */}
            <AnimatePresence mode='popLayout'>
              {activeMode === 'requirements' && (
                <motion.g
                  key='requirements-lines'
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.2 } }}
                >
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.requirements.x}
                    y2={NODES.requirements.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-blue-500 dark:text-blue-400'
                    filter='url(#glow)'
                    strokeDasharray='5,5'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.8, ease: 'easeInOut' }}
                  />
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.srs.x}
                    y2={NODES.srs.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-blue-500 dark:text-blue-400'
                    filter='url(#glow)'
                    strokeDasharray='5,5'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{
                      duration: 0.8,
                      ease: 'easeInOut',
                      delay: 0.1,
                    }}
                  />
                  <motion.line
                    x1={NODES.requirements.x}
                    y1={NODES.requirements.y}
                    x2={NODES.srs.x}
                    y2={NODES.srs.y}
                    stroke='currentColor'
                    strokeWidth='1'
                    className='text-blue-500/50 dark:text-blue-400/50'
                    strokeDasharray='3,3'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{
                      duration: 0.8,
                      ease: 'easeInOut',
                      delay: 0.2,
                    }}
                  />
                </motion.g>
              )}
              {activeMode === 'design' && (
                <motion.g
                  key='design-lines'
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.2 } }}
                >
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.design.x}
                    y2={NODES.design.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-teal-500 dark:text-teal-400'
                    filter='url(#glow)'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.8, ease: 'easeInOut' }}
                  />
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.sad.x}
                    y2={NODES.sad.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-teal-500 dark:text-teal-400'
                    filter='url(#glow)'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{
                      duration: 0.8,
                      ease: 'easeInOut',
                      delay: 0.2,
                    }}
                  />
                  <motion.line
                    x1={NODES.srs.x}
                    y1={NODES.srs.y}
                    x2={NODES.design.x}
                    y2={NODES.design.y}
                    stroke='currentColor'
                    strokeWidth='1'
                    className='text-teal-500/60 dark:text-teal-400/60'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{
                      duration: 0.8,
                      ease: 'easeInOut',
                      delay: 0.4,
                    }}
                  />
                </motion.g>
              )}
              {activeMode === 'testing' && (
                <motion.g
                  key='testing-lines'
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.2 } }}
                >
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.testcase.x}
                    y2={NODES.testcase.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-purple-500 dark:text-purple-400'
                    filter='url(#glow)'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.8 }}
                  />
                  <motion.line
                    x1={CENTER_NODE.x}
                    y1={CENTER_NODE.y}
                    x2={NODES.review.x}
                    y2={NODES.review.y}
                    stroke='currentColor'
                    strokeWidth='2'
                    className='text-purple-500 dark:text-purple-400'
                    filter='url(#glow)'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.8 }}
                  />
                  <motion.line
                    x1={NODES.design.x}
                    y1={NODES.design.y}
                    x2={NODES.testcase.x}
                    y2={NODES.testcase.y}
                    stroke='currentColor'
                    strokeWidth='1'
                    className='text-purple-500/60 dark:text-purple-400/60'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1, delay: 0.3 }}
                  />
                  <motion.line
                    x1={NODES.srs.x}
                    y1={NODES.srs.y}
                    x2={NODES.testcase.x}
                    y2={NODES.testcase.y}
                    stroke='currentColor'
                    strokeWidth='1'
                    className='text-purple-500/60 dark:text-purple-400/60'
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1, delay: 0.3 }}
                  />
                </motion.g>
              )}
            </AnimatePresence>

            {/* 2. 중앙 노드 (원형 배경) 및 라벨 */}
            <motion.circle
              cx={CENTER_NODE.x}
              cy={CENTER_NODE.y}
              r='48'
              fill='currentColor'
              className={`transition-colors duration-500 ${activeMode === 'requirements' ? 'text-blue-500/10' : ''} ${activeMode === 'design' ? 'text-teal-500/10' : ''} ${activeMode === 'testing' ? 'text-purple-500/10' : ''} `}
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              filter='url(#glow)'
            />
            <motion.circle
              cx={CENTER_NODE.x}
              cy={CENTER_NODE.y}
              r='40'
              fill='var(--bg-primary)'
              stroke='currentColor'
              strokeWidth='2'
              className={`transition-colors duration-500 ${activeMode === 'requirements' ? 'text-blue-500 dark:text-blue-400' : ''} ${activeMode === 'design' ? 'text-teal-500 dark:text-teal-400' : ''} ${activeMode === 'testing' ? 'text-purple-500 dark:text-purple-400' : ''} `}
              filter='url(#glow)'
            />
            <text
              x={CENTER_NODE.x}
              y={CENTER_NODE.y}
              textAnchor='middle'
              dominantBaseline='middle'
              className='fill-fg-primary text-sm font-bold'
            >
              {CENTER_NODE.label}
            </text>

            {/* 3. 각 모드에 해당하는 주변 노드 표기 */}
            {[
              NODES.requirements,
              NODES.srs,
              NODES.design,
              NODES.sad,
              NODES.testcase,
              NODES.review,
            ].map((node) => {
              // 노드의 활성화 여부 계산 (현재 모드에 맞춰 색상 다르게)
              const isActiveInRequirements =
                activeMode === 'requirements' &&
                (node === NODES.requirements || node === NODES.srs || node === NODES.review);
              const isActiveInDesign =
                activeMode === 'design' &&
                (node === NODES.srs || node === NODES.design || node === NODES.sad);
              const isActiveInTesting =
                activeMode === 'testing' &&
                (node === NODES.testcase ||
                  node === NODES.review ||
                  node === NODES.design ||
                  node === NODES.srs);

              const isActive = isActiveInRequirements || isActiveInDesign || isActiveInTesting;

              const activeColorClass = isActiveInRequirements
                ? 'text-blue-500 dark:text-blue-400'
                : isActiveInDesign
                  ? 'text-teal-500 dark:text-teal-400'
                  : isActiveInTesting
                    ? 'text-purple-500 dark:text-purple-400'
                    : 'text-line-primary dark:text-line-subtle';

              const labelSizeClass = node.label.length > 5 ? 'text-[10px]' : 'text-xs';

              return (
                <motion.g
                  key={node.label}
                  initial={{ opacity: isActive ? 1 : 0.4 }}
                  animate={{ opacity: isActive ? 1 : 0.4 }}
                  transition={{ duration: 0.5 }}
                >
                  {/* 활성화된 노드의 펄스 효과 */}
                  {isActive && (
                    <motion.circle
                      cx={node.x}
                      cy={node.y}
                      r='30'
                      fill='currentColor'
                      className={activeColorClass}
                      initial={{ opacity: 0.4, scale: 1 }}
                      animate={{ opacity: 0, scale: 1.6 }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        ease: 'easeOut',
                      }}
                    />
                  )}
                  <motion.circle
                    cx={node.x}
                    cy={node.y}
                    r='30'
                    fill='transparent'
                    stroke='currentColor'
                    strokeWidth='2'
                    className={activeColorClass}
                    filter={isActive ? 'url(#glow)' : undefined}
                  />
                  <text
                    x={node.x}
                    y={node.y - 40}
                    textAnchor='middle'
                    className={`${labelSizeClass} font-semibold ${isActive ? 'fill-fg-primary' : 'fill-fg-secondary'}`}
                  >
                    {node.label}
                  </text>
                </motion.g>
              );
            })}
          </svg>

          {/* 모바일 화면을 위해 하단에 현재 모드 이름 표기 (데스크탑에선 생략) */}
          <div className='text-fg-muted absolute bottom-[-10px] text-sm font-bold tracking-[0.2em] uppercase lg:hidden'>
            {activeModeData.title}
          </div>
        </div>

        {/* === 우측: 조작부 및 텍스트 전환 영역 === */}
        <div className='z-10 flex w-full flex-1 flex-col items-center space-y-8 lg:max-w-xl lg:items-start'>
          {/* 모드 선택기 버튼형 탭 (글씨가 길어져서 레이아웃 조정) */}
          <div className='bg-canvas-secondary flex w-fit flex-wrap justify-center gap-1 rounded-3xl p-1 lg:justify-start'>
            {MODES.map((mode) => {
              const isActive = activeMode === mode.id;
              return (
                <Button
                  variant={'ghost'}
                  key={mode.id}
                  onClick={() => setActiveMode(mode.id)}
                  className={`relative z-10 rounded-full px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-colors duration-200 sm:px-6 sm:text-xs ${
                    isActive
                      ? 'text-canvas-primary hover:text-canvas-primary'
                      : 'text-fg-secondary hover:text-fg-primary'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId='showcase-active-tab'
                      className='bg-fg-primary absolute inset-0 -z-10 rounded-full'
                      transition={{
                        type: 'spring',
                        stiffness: 300,
                        damping: 30,
                      }}
                    />
                  )}
                  {mode.title}
                </Button>
              );
            })}
          </div>

          {/* 슬라이드 업 텍스트 컨테이너 (고정 높이로 밀림 현상 방지) */}
          <div className='pointer-events-none relative min-h-[160px] w-full overflow-hidden text-center lg:text-left'>
            <AnimatePresence mode='wait'>
              <motion.div
                key={activeMode}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                className='pointer-events-auto absolute inset-0 flex flex-col gap-4 px-2'
              >
                <h3 className='text-fg-primary text-2xl font-bold tracking-tight'>
                  {activeModeData.title}
                </h3>
                <p className='text-md text-fg-secondary break-keep'>{activeModeData.description}</p>
                <div className='mt-2 flex flex-wrap justify-center gap-2 sm:gap-3 lg:justify-start'>
                  {activeModeData.badges.map((badge, idx) => (
                    <span
                      key={idx}
                      className='border-line-primary bg-canvas-primary text-fg-secondary rounded-full border px-3 py-1 text-xs font-medium whitespace-nowrap'
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
