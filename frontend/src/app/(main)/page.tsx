import { AgentShowcase } from '@/components/landing/AgentShowcase';
import { HeroSection } from '@/components/landing/HeroSection';
import { OrchestrationShowcase } from '@/components/landing/OrchestrationShowcase';
import { Footer } from '@/components/layout/Footer';

export default function LandingPage() {
  return (
    <div className='bg-canvas-primary flex min-h-screen flex-col'>
      <main className='flex flex-1 flex-col'>
        <HeroSection />
        <OrchestrationShowcase autoPlay={true} interval={5000} />
        <AgentShowcase />
      </main>
      <Footer />
    </div>
  );
}
