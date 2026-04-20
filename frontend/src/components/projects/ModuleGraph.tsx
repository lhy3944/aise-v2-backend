'use client';

import { cn } from '@/lib/utils';
import type { ProjectModule } from '@/types/project';

const MODULE_NODES: {
  value: ProjectModule;
  label: string;
  description: string;
}[] = [
  {
    value: 'requirements',
    label: 'Requirements',
    description: '요구사항 관리 + SRS 생성',
  },
  {
    value: 'design',
    label: 'Design',
    description: 'UCD/UCS/SAD 설계 문서',
  },
  {
    value: 'testcase',
    label: 'Test Case',
    description: '테스트 케이스 자동 생성',
  },
];

// Edges: from → to
const EDGES: [ProjectModule, ProjectModule][] = [
  ['requirements', 'design'],
  ['requirements', 'testcase'],
];

interface ModuleGraphProps {
  modules: ProjectModule[];
}

export function ModuleGraph({ modules }: ModuleGraphProps) {
  return (
    <div className='border-line-subtle rounded-md border p-3'>
      {/* Desktop/Tablet: horizontal SVG graph */}
      <div className='hidden sm:block'>
        <HorizontalGraph modules={modules} />
      </div>
      {/* Mobile: vertical SVG graph */}
      <div className='block sm:hidden'>
        <VerticalGraph modules={modules} />
      </div>
    </div>
  );
}

// --- Shared animated edge styles ---
const EDGE_DASH = '3,3';
const EDGE_ANIM_DURATION = '1.2s';

function AnimatedEdge({
  x1,
  y1,
  x2,
  y2,
  active,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  active: boolean;
}) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke='currentColor'
      strokeWidth={active ? 1.5 : 1}
      strokeDasharray={EDGE_DASH}
      className={cn(
        'transition-colors duration-300',
        active ? 'text-accent-primary' : 'text-fg-muted/30',
      )}
    >
      {active && (
        <animate
          attributeName='stroke-dashoffset'
          from='18'
          to='0'
          dur={EDGE_ANIM_DURATION}
          repeatCount='indefinite'
        />
      )}
    </line>
  );
}

// --- Horizontal layout (desktop) ---
function HorizontalGraph({ modules }: { modules: ProjectModule[] }) {
  const nodeW = 120;
  const nodeH = 32;
  const pad = 10;

  const positions: Record<ProjectModule, { x: number; y: number }> = {
    requirements: { x: 100, y: 60 },
    design: { x: 300, y: 30 },
    testcase: { x: 300, y: 90 },
  };

  const allX = Object.values(positions).map((p) => p.x);
  const allY = Object.values(positions).map((p) => p.y);
  const minX = Math.min(...allX) - nodeW / 2 - pad;
  const minY = Math.min(...allY) - nodeH / 2 - pad;
  const maxX = Math.max(...allX) + nodeW / 2 + pad;
  const maxY = Math.max(...allY) + nodeH / 2 + pad;

  return (
    <svg
      viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
      className='h-auto w-full'
      aria-label='Module graph'
    >
      <defs>
        <filter id='node-glow' x='-30%' y='-30%' width='160%' height='160%'>
          <feGaussianBlur stdDeviation='0.2' result='blur' />
          <feComposite in='SourceGraphic' in2='blur' operator='over' />
        </filter>
      </defs>
      {/* Edges */}
      {EDGES.map(([from, to]) => {
        const active = modules.includes(from) && modules.includes(to);
        return (
          <AnimatedEdge
            key={`${from}-${to}`}
            x1={positions[from].x + nodeW / 2}
            y1={positions[from].y}
            x2={positions[to].x - nodeW / 2}
            y2={positions[to].y}
            active={active}
          />
        );
      })}

      {/* Nodes */}
      {MODULE_NODES.map((node) => {
        const active = modules.includes(node.value);
        const pos = positions[node.value];
        return (
          <g key={node.value} className='transition-opacity duration-300'>
            <NodeBox
              x={pos.x}
              y={pos.y}
              label={node.label}
              description={node.description}
              active={active}
              width={nodeW}
              height={nodeH}
            />
          </g>
        );
      })}
    </svg>
  );
}

// --- Vertical layout (mobile) ---
function VerticalGraph({ modules }: { modules: ProjectModule[] }) {
  const W = 300;
  const H = 260;

  const positions: Record<ProjectModule, { x: number; y: number }> = {
    requirements: { x: 150, y: 38 },
    design: { x: 78, y: 190 },
    testcase: { x: 222, y: 190 },
  };

  const nodeW = 130;
  const nodeH = 52;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className='h-auto w-full'
      aria-label='Module graph'
    >
      <defs>
        <filter
          id='node-glow-mobile'
          x='-30%'
          y='-30%'
          width='160%'
          height='160%'
        >
          <feGaussianBlur stdDeviation='0.2' result='blur' />
          <feComposite in='SourceGraphic' in2='blur' operator='over' />
        </filter>
      </defs>
      {/* Edges */}
      {EDGES.map(([from, to]) => {
        const active = modules.includes(from) && modules.includes(to);
        return (
          <AnimatedEdge
            key={`${from}-${to}`}
            x1={positions[from].x}
            y1={positions[from].y + nodeH / 2}
            x2={positions[to].x}
            y2={positions[to].y - nodeH / 2}
            active={active}
          />
        );
      })}

      {/* Nodes */}
      {MODULE_NODES.map((node) => {
        const active = modules.includes(node.value);
        const pos = positions[node.value];
        return (
          <g key={node.value}>
            <MobileNodeBox
              x={pos.x}
              y={pos.y}
              label={node.label}
              description={node.description}
              active={active}
              width={nodeW}
              height={nodeH}
            />
          </g>
        );
      })}
    </svg>
  );
}

// --- Node components ---
function NodeBox({
  x,
  y,
  label,
  description,
  active,
  width,
  height,
}: {
  x: number;
  y: number;
  label: string;
  description: string;
  active: boolean;
  width: number;
  height: number;
}) {
  return (
    <g opacity={active ? 1 : 0.3} className='transition-opacity duration-300'>
      <rect
        x={x - width / 2}
        y={y - height / 2}
        width={width}
        height={height}
        rx={6}
        fill='transparent'
        className={cn(
          'transition-colors duration-300',
          active ? 'stroke-accent-primary' : 'stroke-line-primary',
        )}
        strokeWidth={active ? 0.8 : 0.5}
        filter={active ? 'url(#node-glow)' : undefined}
      />
      <text
        x={x}
        y={y - 3}
        textAnchor='middle'
        className={cn(
          'text-[8px] font-medium',
          active ? 'fill-fg-primary' : 'fill-fg-muted',
        )}
      >
        {label}
      </text>
      <text
        x={x}
        y={y + 7}
        textAnchor='middle'
        className={cn(
          'text-[5.5px]',
          active ? 'fill-fg-secondary' : 'fill-fg-muted',
        )}
      >
        {description}
      </text>
    </g>
  );
}

function MobileNodeBox({
  x,
  y,
  label,
  description,
  active,
  width,
  height,
}: {
  x: number;
  y: number;
  label: string;
  description: string;
  active: boolean;
  width: number;
  height: number;
}) {
  return (
    <g opacity={active ? 1 : 0.3} className='transition-opacity duration-300'>
      <rect
        x={x - width / 2}
        y={y - height / 2}
        width={width}
        height={height}
        rx={8}
        fill='transparent'
        className={cn(
          'transition-colors duration-300',
          active ? 'stroke-accent-primary' : 'stroke-line-primary',
        )}
        strokeWidth={active ? 1.2 : 0.7}
        filter={active ? 'url(#node-glow-mobile)' : undefined}
      />
      <text
        x={x}
        y={y - 4}
        textAnchor='middle'
        className={cn(
          'text-[13px] font-semibold',
          active ? 'fill-fg-primary' : 'fill-fg-muted',
        )}
      >
        {label}
      </text>
      <text
        x={x}
        y={y + 12}
        textAnchor='middle'
        className={cn(
          'text-[9px]',
          active ? 'fill-fg-secondary' : 'fill-fg-muted',
        )}
      >
        {description}
      </text>
    </g>
  );
}
