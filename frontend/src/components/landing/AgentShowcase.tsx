import { AgentCard } from '@/components/shared/AgentCard';
import { BookOpen, ClipboardList, Code, FileText, MessageSquareMore, Search } from 'lucide-react';

const agents = [
  {
    icon: ClipboardList,
    name: 'Requirements',
    description:
      '자연어로 입력한 요구사항을 AI가 분석하여 기능/품질/제약사항으로 자동 분류하고, 누락된 항목을 제안합니다.',
    tags: ['FR/QA/Constraints', 'Glossary', 'AI 정제'],
  },
  {
    icon: Code,
    name: 'SRS',
    description:
      '정제된 요구사항을 기반으로 표준 형식의 SRS 문서를 자동 생성합니다. 버전 관리와 추적성을 지원합니다.',
    tags: ['자동 생성', '버전 관리', '추적성'],
  },
  {
    icon: FileText,
    name: 'Design',
    description:
      '요구사항 기반으로 Use Case Diagram, Interaction Diagram 등 시스템 모델을 자동 생성합니다.',
    tags: ['UCD', 'UCS', 'System Models'],
  },
  {
    icon: BookOpen,
    name: 'SAD',
    description: '논리/동적/물리 모델을 종합하여 Software Architecture Document를 생성합니다.',
    tags: ['Logical', 'Physical', 'Dynamic', 'Architecture'],
  },
  {
    icon: Search,
    name: 'Test Case',
    description:
      '요구사항 기반으로 테스트 케이스를 자동 생성합니다. 독립모드와 연동모드를 모두 지원합니다.',
    tags: ['연동모드', '독립모드', 'Export'],
  },
  {
    icon: MessageSquareMore,
    name: 'AI Review',
    description:
      '각 단계별 산출물의 품질을 AI가 검토하고, 개선 사항을 제안합니다. 부실한 입력을 사전에 방지합니다.',
    tags: ['품질 검증', '개선 제안', 'Cross-cutting'],
  },
];

export function AgentShowcase() {
  return (
    <section className='flex flex-col items-center gap-2.5 px-4 pb-6 sm:px-8 md:px-12'>
      <div className='border-line-subtle flex items-center gap-2 rounded-full border px-4 py-1.5'>
        <span className='bg-accent-primary h-1.5 w-1.5 rounded-full' />
        <span className='text-fg-secondary text-xs tracking-wide'>AI Agents</span>
      </div>
      <div className='grid w-full max-w-[960px] grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3'>
        {agents.map((agent) => (
          <AgentCard key={agent.name} {...agent} />
        ))}
      </div>
    </section>
  );
}
