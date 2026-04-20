import { Button } from "@/components/ui/button";
import { ArrowRight, BookOpen, Play, SquareArrowRight } from "lucide-react";
import Link from "next/link";
import { AuroraText } from "../ui/aurora-text";
import { TextAnimate } from "../ui/text-animate";

export function HeroSection() {
  return (
    <section className="flex flex-col items-center gap-7 px-12 py-12">
      <div className="flex flex-col items-center gap-5">
        <h1 className="text-fg-primary text-center text-6xl font-semibold tracking-wide">
          Introducing AISE
          <AuroraText className="absolute bottom-6 left-1">+</AuroraText>
        </h1>
        <div className="text-md text-fg-secondary max-w-[560px] text-center leading-relaxed font-semibold">
          <TextAnimate animation="slideLeft" by="character">
            AI 에이전트와 함께 요구사항부터 테스트까지
          </TextAnimate>
          <TextAnimate animation="slideLeft" by="character">
            소프트웨어 엔지니어링을 자동화하세요.
          </TextAnimate>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <Button asChild size="lg" className="rounded-sm px-7">
          <Link href="/projects">
            <SquareArrowRight className="size-4" />
            Get Started
          </Link>
        </Button>
        <Button
          asChild
          size="lg"
          className="rounded-sm px-7"
          variant={"outline"}
        >
          <Link href="/dashboard">
            <BookOpen className="size-4" />
            Documentation
          </Link>
        </Button>
        {/* <Button
          variant='outline'
          size='lg'
          className='gap-2 rounded-lg border-line-primary px-7'
        >
          <Play className='h-4 w-4' />
          Watch Demo
        </Button> */}
      </div>
    </section>
  );
}
