'use client';

import Image from 'next/image';
import Link from 'next/link';

interface LogoProps {
  showName?: boolean;
}

export function Logo({ showName = false }: LogoProps) {
  return (
    <Link href='/' className='flex items-center gap-2'>
      {/* 라이트 모드 로고 */}
      <Image
        src='/logo_icon_light.png'
        alt='AISE logo'
        width={36}
        height={36}
        priority
        className='size-6 sm:size-9 dark:hidden'
      />

      {/* 다크 모드 로고 */}
      <Image
        src='/logo_icon.png'
        alt='AISE logo'
        width={36}
        height={36}
        priority
        className='hidden size-6 sm:size-9 dark:block'
      />
      <div className={`relative ml-1 items-center`}>
        <span className={`text-sm font-bold sm:text-2xl`}>AISE</span>
        <span className='absolute -top-0.5 -right-2 text-xs font-bold sm:-top-1.5 sm:-right-3.5 sm:text-lg'>
          +
        </span>
      </div>
    </Link>
  );
}
