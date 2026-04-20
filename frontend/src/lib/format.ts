export function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function formatRelativeTime(dateStr: string) {
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (seconds < 60) return '방금';
  if (minutes < 60) return `${minutes}분 전`;
  if (hours < 24) return `${hours}시간 전`;
  if (days < 30) return `${days}일 전`;
  if (months < 12) return `${months}달 전`;
  return `${years}년 전`;
}

export function formatDateTime(dateStr: string, options?: { hour12?: boolean }) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: options?.hour12,
  });
}

const FORMAT_TOKENS: Record<string, Intl.DateTimeFormatOptions> = {
  YYYY: { year: 'numeric' },
  MM: { month: '2-digit' },
  DD: { day: '2-digit' },
  HH: { hour: '2-digit', hour12: false },
  mm: { minute: '2-digit' },
  ss: { second: '2-digit' },
};

export function formatDateBy(dateStr: string, format: string) {
  const date = new Date(dateStr);
  let result = format;
  for (const [token, opts] of Object.entries(FORMAT_TOKENS)) {
    if (result.includes(token)) {
      const value = new Intl.DateTimeFormat('ko-KR', opts).format(date);
      result = result.replace(token, value);
    }
  }
  return result;
}
