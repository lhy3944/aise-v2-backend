'use client';

import { Moon, Sun } from 'lucide-react';
import { Switch as SwitchPrimitive } from 'radix-ui';
import useIsMounted from '@/hooks/useIsMounted';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  className?: string;
}

export function ThemeToggle({
  checked,
  onCheckedChange,
  className,
}: ThemeToggleProps) {
  const isMounted = useIsMounted();
  const effectiveChecked = checked && isMounted;

  const handleChange = (newChecked: boolean) => {
    onCheckedChange(newChecked);
  };

  return (
    <SwitchPrimitive.Root
      data-slot='switch'
      checked={effectiveChecked}
      onCheckedChange={handleChange}
      aria-label='Toggle theme'
      className={cn(
        'relative inline-flex h-5 w-[46px] shrink-0 cursor-pointer items-center rounded-full',
        'border border-transparent shadow-xs outline-none',
        'transition-colors duration-300 ease-in-out',
        'active:scale-95',
        'data-[state=checked]:bg-foreground data-[state=unchecked]:bg-input dark:data-[state=unchecked]:bg-input/80',
        className,
      )}
    >
      <SwitchPrimitive.Thumb
        data-slot='switch-thumb'
        className={cn(
          'pointer-events-none relative flex items-center justify-center overflow-hidden',
          'size-4 rounded-full shadow-sm ring-0',
          'transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
          'bg-background dark:data-[state=checked]:bg-background',
          'data-[state=checked]:translate-x-[26px] data-[state=unchecked]:translate-x-0.5',
          isMounted ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      >
        <Sun
          className={cn(
            'text-muted-foreground absolute size-3.5 transition-all duration-300',
            effectiveChecked
              ? 'scale-0 rotate-90 opacity-0'
              : 'scale-100 rotate-0 opacity-100',
          )}
        />
        <Moon
          fill='currentColor'
          className={cn(
            'absolute size-3.5 transition-all duration-300',
            effectiveChecked
              ? 'scale-100 rotate-0 opacity-100'
              : 'scale-0 -rotate-90 opacity-0',
          )}
        />
      </SwitchPrimitive.Thumb>
    </SwitchPrimitive.Root>
  );
}
