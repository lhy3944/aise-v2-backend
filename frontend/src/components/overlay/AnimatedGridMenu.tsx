'use client';

import { Plus, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { AnimatePresence, motion, type Variants } from 'motion/react';
import { useState, useRef, useEffect } from 'react';
import { type ReactNode } from 'react';
import { Button } from '@/components/ui/button';


export interface GridMenuItem {
  id: string;
  label: string;
  icon: LucideIcon;
  iconColor?: string;
  onClick?: () => void;
}

export interface AnimatedGridMenuProps {
  /** The items to display in the grid */
  items: GridMenuItem[];
  /** Title shown at the top of the menu */
  title?: string;
  /** Custom trigger element (overrides the default Plus button) */
  trigger?: ReactNode;
  /** Additional CSS classes for the container */
  className?: string;
  /** Additional CSS classes for the floating dropdown content */
  contentClassName?: string;
  /** Number of columns for the grid (default: 3) */
  columns?: 2 | 3 | 4;
}

// Animation variants
const menuVariants: Variants = {
  hidden: { opacity: 0, scale: 0.9, y: 10, transformOrigin: 'top right' },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 260,
      damping: 20,
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: { duration: 0.2 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.3, ease: 'easeOut' },
  },
};

export function AnimatedGridMenu({
  items,
  title = 'Create new',
  trigger,
  className = '',
  contentClassName = 'top-12 right-0 origin-top-right',
  columns = 3,
}: AnimatedGridMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  return (
    <div className={`relative inline-block ${className}`} ref={containerRef}>
      {/* Trigger Button */}
      <div onClick={() => setIsOpen(!isOpen)} className='inline-block cursor-pointer'>
        {trigger ? (
          trigger
        ) : (
          <Button
            variant='default'
            size='icon'
            className='bg-accent-primary hover:bg-accent-primary/90 rounded-full text-white shadow-md'
            aria-label={title}
          >
            <Plus
              className={`h-5 w-5 transition-transform duration-300 ${isOpen ? 'rotate-45' : 'rotate-0'}`}
            />
          </Button>
        )}
      </div>

      {/* Expanded Grid Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            variants={menuVariants}
            initial='hidden'
            animate='visible'
            exit='exit'
            className={`bg-popover text-popover-foreground border-border absolute z-100 w-[320px] overflow-hidden rounded-xl border p-2 shadow-md ${contentClassName}`}
          >
            {/* Header */}
            {title && (
              <div className='border-border/50 flex items-center justify-between border-b px-4 py-3'>
                <h3 className='text-sm font-semibold'>{title}</h3>
                <button
                  onClick={() => setIsOpen(false)}
                  className='text-muted-foreground hover:text-foreground p-1 transition-colors'
                  aria-label='Close menu'
                >
                  <X className='h-5 w-5' />
                </button>
              </div>
            )}

            {/* Grid */}
            <div
              className='grid p-2'
              style={{
                gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
              }}
            >
              {items.map((item: GridMenuItem, index: number) => {
                // Determine border classes based on position to create inner borders only
                const rows = Math.ceil(items.length / columns);
                const isBottomRow = Math.floor(index / columns) === rows - 1;
                const isRightCol = index % columns === columns - 1;

                return (
                  <motion.button
                    key={item.id}
                    variants={itemVariants}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      if (item.onClick) item.onClick();
                      setIsOpen(false);
                    }}
                    className={`group hover:bg-accent relative flex flex-col items-center justify-center gap-3 py-5 transition-all duration-200 hover:z-10 hover:rounded-xl hover:border-transparent ${!isBottomRow ? 'border-border/50 border-b' : ''} ${!isRightCol ? 'border-border/50 border-r' : ''} `}
                  >
                    <item.icon
                      className={`h-6 w-6 transition-colors ${item.iconColor || 'text-muted-foreground group-hover:text-foreground'}`}
                    />
                    <span className='text-muted-foreground group-hover:text-foreground text-[13px] font-semibold transition-colors'>
                      {item.label}
                    </span>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
