import { OverlayProvider } from '@/components/providers/OverlayProvider';
import { StoreProvider } from '@/components/providers/StoreProvider';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { fontVariables } from '@/lib/fonts';
import type { Metadata, Viewport } from 'next';
import { ThemeProvider } from 'next-themes';
import NextTopLoader from 'nextjs-toploader';
import './globals.css';

export const metadata: Metadata = {
  title: 'AISE+',
  description: 'AI Agent Development Platform',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  interactiveWidget: 'resizes-content',
};

const themeScript = `
  (function() {
    try {
      var theme = localStorage.getItem('aise-theme');
      if (theme === '"light"' || theme === 'light') {
        document.documentElement.classList.remove('dark');
      } else {
        document.documentElement.classList.add('dark');
      }
    } catch(e) {
      document.documentElement.classList.add('dark');
    }
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const topLoaderOptions = {
    color: 'var(--accent-primary)',
    showSpinner: false,
    height: 2,
  };

  return (
    <html lang='ko' suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${fontVariables} font-medium antialiased`}>
        <NextTopLoader {...topLoaderOptions} />
        <StoreProvider>
          <ThemeProvider attribute='class' defaultTheme='dark' enableSystem storageKey='aise-theme'>
            <TooltipProvider>
              {children}
              <OverlayProvider />
              <Toaster position='bottom-right' closeButton={false} />
            </TooltipProvider>
          </ThemeProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
