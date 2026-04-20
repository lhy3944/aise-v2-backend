/**
 * HTTP 환경(localhost 등)에서 navigator.clipboard API가 없는 경우
 * textarea + execCommand('copy') fallback을 제공하는 polyfill.
 *
 * 앱 초기화 시 한 번 호출하면 Streamdown 내장 copy 버튼 등
 * navigator.clipboard.writeText를 사용하는 모든 코드에 적용됨.
 */
export function installClipboardPolyfill() {
  if (typeof window === 'undefined') return;
  try {
    // Secure context에서는 clipboard API가 정상 동작하므로 polyfill 불필요
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') return;
  } catch {
    // clipboard 접근 자체가 차단된 경우 polyfill 적용
  }

  const fallbackWriteText = async (text: string): Promise<void> => {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  };

  if (!navigator.clipboard) {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: fallbackWriteText },
      writable: true,
      configurable: true,
    });
  } else {
    navigator.clipboard.writeText = fallbackWriteText;
  }
}
