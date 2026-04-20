import Link from 'next/link';

export default function NotFound() {
  return (
    <div className='bg-canvas-primary flex min-h-screen flex-col items-center justify-center'>
      <h1 className='text-fg-primary text-6xl font-bold'>404</h1>
      <p className='text-fg-secondary mt-4 text-lg'>페이지를 찾을 수 없습니다.</p>
      <Link
        href='/'
        className='bg-accent-primary mt-8 rounded-lg px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90'
      >
        홈으로 돌아가기
      </Link>
    </div>
  );
}
