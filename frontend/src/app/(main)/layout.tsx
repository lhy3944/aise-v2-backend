import { Header } from '@/components/layout/Header';

export default function MainLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className='flex h-dvh flex-col'>
      <Header showLayoutToggle />
      {children}
    </div>
  );
}
