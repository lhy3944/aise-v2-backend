/** 레이아웃 너비 설정 */
export const LAYOUT_MAX_W_DEFAULT = 'max-w-6xl';
export const LAYOUT_MAX_W_NORMAL = 'max-w-[1480px]';
export const LAYOUT_MAX_W_WIDE = 'max-w-[2160px]';

/** fullWidthMode에 따른 max-width 클래스 반환 */
export function layoutMaxW(fullWidthMode: boolean) {
  return fullWidthMode ? LAYOUT_MAX_W_WIDE : LAYOUT_MAX_W_DEFAULT;
}

export function layoutMaxWNormal(fullWidthMode: boolean) {
  return fullWidthMode ? LAYOUT_MAX_W_NORMAL : LAYOUT_MAX_W_DEFAULT;
}
