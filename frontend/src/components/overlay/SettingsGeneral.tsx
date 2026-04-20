'use client';

import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import {
  CHAT_FONT_SIZE_OPTIONS,
  type ChatFontSize,
} from '@/config/chat-font-size';
import {
  MARKDOWN_THEME_OPTIONS,
  type MarkdownThemePreset,
} from '@/config/markdown-theme';
import { cn } from '@/lib/utils';
import { useUiPreferenceStore } from '@/stores/ui-preference-store';
import { useTheme } from 'next-themes';

const THEME_OPTIONS = [
  { value: 'light', label: '라이트' },
  { value: 'dark', label: '다크' },
  { value: 'system', label: '시스템' },
] as const;

function ThemePreview({ mode }: { mode: 'light' | 'dark' }) {
  const isLight = mode === 'light';

  return (
    <div
      className={cn(
        'flex h-12 w-full max-w-20 flex-col gap-1.5 rounded-md border p-2',
        isLight ? 'border-gray-200 bg-gray-100' : 'border-gray-700 bg-gray-800',
      )}
    >
      <div
        className={cn(
          'h-1.5 w-3/4 rounded-sm',
          isLight ? 'bg-gray-300' : 'bg-gray-600',
        )}
      />
      <div
        className={cn(
          'h-1.5 w-1/2 rounded-sm',
          isLight ? 'bg-gray-300' : 'bg-gray-600',
        )}
      />
      <div
        className={cn(
          'h-1.5 w-2/3 rounded-sm',
          isLight ? 'bg-gray-300' : 'bg-gray-600',
        )}
      />
    </div>
  );
}

function SystemThemePreview() {
  return (
    <div className='flex h-12 w-full overflow-hidden rounded-md border border-gray-500'>
      <div className='flex w-1/2 flex-col gap-1.5 bg-gray-100 p-2'>
        <div className='h-1.5 w-3/4 rounded-sm bg-gray-300' />
        <div className='h-1.5 w-1/2 rounded-sm bg-gray-300' />
        <div className='h-1.5 w-2/3 rounded-sm bg-gray-300' />
      </div>
      <div className='flex w-1/2 flex-col gap-1.5 bg-gray-800 p-2'>
        <div className='h-1.5 w-3/4 rounded-sm bg-gray-600' />
        <div className='h-1.5 w-1/2 rounded-sm bg-gray-600' />
        <div className='h-1.5 w-2/3 rounded-sm bg-gray-600' />
      </div>
    </div>
  );
}

const optionCardClass =
  'bg-canvas-primary hover:bg-canvas-surface rounded-lg border border-border p-3 text-left transition-colors';
const optionCardSelectedClass =
  'ring-accent-primary border-accent-primary bg-canvas-surface ring-1';

export function SettingsGeneral() {
  const { theme, setTheme } = useTheme();
  const markdownTheme = useUiPreferenceStore((s) => s.markdownTheme);
  const chatFontSize = useUiPreferenceStore((s) => s.chatFontSize);
  const setMarkdownTheme = useUiPreferenceStore((s) => s.setMarkdownTheme);
  const setChatFontSize = useUiPreferenceStore((s) => s.setChatFontSize);

  return (
    <div className='flex flex-col gap-6'>
      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>일반</h3>
        <div className='flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <Label className='text-fg-secondary text-sm'>언어</Label>
            <Select defaultValue='ko'>
              <SelectTrigger className='w-[160px]'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='ko'>한국어</SelectItem>
                <SelectItem value='en'>English</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>테마</h3>
        <div className='grid grid-cols-3 gap-3 px-4'>
          {THEME_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type='button'
              onClick={() => setTheme(value)}
              className={cn(
                'rounded-lg border border-border p-2 transition-colors',
                'flex flex-col items-center gap-2',
                theme === value
                  ? 'ring-accent-primary border-accent-primary bg-canvas-surface ring-1'
                  : 'hover:bg-canvas-surface/50',
              )}
            >
              {value === 'system' ? (
                <SystemThemePreview />
              ) : (
                <ThemePreview mode={value} />
              )}
              <span
                className={cn(
                  'text-xs',
                  theme === value ? 'font-medium' : 'text-fg-secondary',
                )}
              >
                {label}
              </span>
            </button>
          ))}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>Markdown</h3>
        <div className='space-y-4'>
          <div className='flex items-center justify-between gap-3'>
            <Label className='text-fg-secondary text-sm'>
              마크다운 스타일 프리셋
            </Label>
            <Select
              value={markdownTheme}
              onValueChange={(value) =>
                setMarkdownTheme(value as MarkdownThemePreset)
              }
            >
              <SelectTrigger className='w-[180px]'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MARKDOWN_THEME_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className='grid grid-cols-1 gap-2 px-4 sm:grid-cols-3'>
            {MARKDOWN_THEME_OPTIONS.map((option) => (
              <button
                key={option.value}
                type='button'
                onClick={() => setMarkdownTheme(option.value)}
                className={cn(
                  optionCardClass,
                  markdownTheme === option.value && optionCardSelectedClass,
                )}
              >
                <p
                  className={cn(
                    'text-sm',
                    markdownTheme === option.value
                      ? 'font-medium'
                      : 'text-fg-primary',
                  )}
                >
                  {option.label}
                </p>
                <p className='text-fg-muted mt-1 text-xs leading-relaxed'>
                  {option.description}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <Separator />

      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>대화</h3>
        <div className='space-y-4'>
          <div className='flex items-center justify-between gap-3'>
            <Label className='text-fg-secondary text-sm'>대화 폰트 크기</Label>
            <Select
              value={chatFontSize}
              onValueChange={(value) => setChatFontSize(value as ChatFontSize)}
            >
              <SelectTrigger className='w-[180px]'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHAT_FONT_SIZE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className='grid grid-cols-1 gap-2 px-4 sm:grid-cols-3'>
            {CHAT_FONT_SIZE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type='button'
                onClick={() => setChatFontSize(option.value)}
                className={cn(
                  optionCardClass,
                  chatFontSize === option.value && optionCardSelectedClass,
                )}
              >
                <p
                  className={cn(
                    'text-sm',
                    chatFontSize === option.value
                      ? 'font-medium'
                      : 'text-fg-primary',
                  )}
                >
                  {option.label}
                </p>
                <p className='text-fg-muted mt-1 text-xs leading-relaxed'>
                  {option.description}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>알림</h3>
        <div className='flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <Label className='text-fg-secondary text-sm'>푸시 알림</Label>
            <Switch defaultChecked />
          </div>
          <div className='flex items-center justify-between'>
            <Label className='text-fg-secondary text-sm'>이메일 알림</Label>
            <Switch />
          </div>
        </div>
      </div>

      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>모델</h3>
        <div className='flex items-center justify-between'>
          <Label className='text-fg-secondary text-sm'>기본 모델</Label>
          <Select defaultValue='gpt-5.4'>
            <SelectTrigger className='w-[160px]'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='gpt-5.4'>GPT-5.4</SelectItem>
              <SelectItem value='claude-sonnet'>Claude Sonnet</SelectItem>
              <SelectItem value='claude-opus'>Claude Opus</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}
