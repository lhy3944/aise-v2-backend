export const CHAT_FONT_SIZE_OPTIONS = [
  {
    value: 'small',
    label: '작게',
    description: '작은 글자 크기',
  },
  {
    value: 'medium',
    label: '중간',
    description: '기본 글자 크기',
  },
  {
    value: 'large',
    label: '크게',
    description: '큰 글자 크기',
  },
] as const;

export type ChatFontSize = (typeof CHAT_FONT_SIZE_OPTIONS)[number]['value'];

export const DEFAULT_CHAT_FONT_SIZE: ChatFontSize = 'medium';

const CHAT_FONT_SIZE_CLASSNAME: Record<ChatFontSize, string> = {
  small: 'text-xs',
  medium: 'text-sm',
  large: 'text-base',
};

const CHAT_FONT_SCALE_CLASSNAME: Record<ChatFontSize, string> = {
  small: 'chat-font-small',
  medium: 'chat-font-medium',
  large: 'chat-font-large',
};

export function getChatFontSizeClassName(size: ChatFontSize): string {
  return CHAT_FONT_SIZE_CLASSNAME[size] ?? CHAT_FONT_SIZE_CLASSNAME[DEFAULT_CHAT_FONT_SIZE];
}

export function getChatFontScaleClassName(size: ChatFontSize): string {
  return CHAT_FONT_SCALE_CLASSNAME[size] ?? CHAT_FONT_SCALE_CLASSNAME[DEFAULT_CHAT_FONT_SIZE];
}
