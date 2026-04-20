import { Inter, Geist_Mono } from 'next/font/google';
import localFont from 'next/font/local';

export const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

export const pretendard = localFont({
  variable: '--font-pretendard',
  display: 'swap',
  preload: true,
  src: [
    {
      path: '../assets/fonts/Pretendard-Thin.woff2',
      weight: '100',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-ExtraLight.woff2',
      weight: '200',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-Light.woff2',
      weight: '300',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-Regular.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-Medium.woff2',
      weight: '500',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-SemiBold.woff2',
      weight: '600',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-Bold.woff2',
      weight: '700',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-ExtraBold.woff2',
      weight: '800',
      style: 'normal',
    },
    {
      path: '../assets/fonts/Pretendard-Black.woff2',
      weight: '900',
      style: 'normal',
    },
  ],
});

export const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const fontVariables = [inter.variable, pretendard.variable, geistMono.variable].join(' ');
