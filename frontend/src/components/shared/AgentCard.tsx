import type { LucideIcon } from 'lucide-react';

interface AgentCardProps {
  icon: LucideIcon;
  name: string;
  description: string;
  tags: string[];
}

export function AgentCard({ icon: Icon, name, description, tags }: AgentCardProps) {
  return (
    <div className='group border-line-subtle hover:bg-card hover:border-accent-primary flex flex-col gap-3 rounded-xl border p-6 transition-colors duration-200'>
      <div className='flex items-center gap-3'>
        <div className='bg-primary dark:bg-canvas-surface flex h-10 w-10 shrink-0 items-center justify-center rounded-lg'>
          <Icon className='h-5 w-5 text-white transition-transform duration-200 group-hover:scale-125' />
        </div>
        <h3 className='text-fg-primary text-sm font-semibold'>{name}</h3>
      </div>
      <p className='text-fg-secondary text-sm leading-relaxed font-medium'>{description}</p>
      <div className='flex flex-1 items-end gap-1.5'>
        {tags.map((tag) => (
          <span key={tag} className='bg-secondary rounded px-2 py-0.5 text-[11px] font-medium'>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
