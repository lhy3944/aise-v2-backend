'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { Check, Forward } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';

/* ── 타입 정의 ── */

export interface QuestionData {
  id?: string;
  /** 탭 헤더에 표시되는 짧은 주제 키워드 (2~8글자 권장) */
  topic?: string;
  question: string;
  type?: 'single' | 'multi' | 'text';
  options?: string[];
  allow_custom?: boolean;
  recommended?: number; // 추천 옵션 인덱스 (0-based)
}

interface QuestionnaireProps {
  questions: QuestionData[];
  onSubmit: (formattedAnswer: string) => void;
}

type AnswerMap = Record<string, SingleAnswer>;

interface SingleAnswer {
  selected: string[];
  customText: string;
}

const EMPTY_ANSWER: SingleAnswer = { selected: [], customText: '' };
const AUTO_NEXT_DELAY_MS = 160;

/* ── 개별 질문 렌더러 ── */

function QuestionItem({
  data,
  answer,
  onChange,
  onAutoNext,
}: {
  data: QuestionData;
  answer: SingleAnswer;
  onChange: (answer: SingleAnswer) => void;
  onAutoNext: () => void;
}) {
  const qType = data.type ?? 'single';
  const options = data.options ?? [];
  const allowCustom = data.allow_custom ?? false;
  const isCustomActive = answer.selected.includes('__custom__');

  const handleOptionClick = (option: string) => {
    if (qType === 'single') {
      onChange({ ...answer, selected: [option], customText: '' });
      window.setTimeout(onAutoNext, AUTO_NEXT_DELAY_MS);
    } else {
      const next = answer.selected.includes(option)
        ? answer.selected.filter((s) => s !== option)
        : [...answer.selected.filter((s) => s !== '__custom__'), option];
      onChange({ ...answer, selected: next });
    }
  };

  const handleCustomToggle = () => {
    if (isCustomActive) {
      onChange({
        ...answer,
        selected: answer.selected.filter((s) => s !== '__custom__'),
        customText: '',
      });
    } else if (qType === 'single') {
      onChange({ ...answer, selected: ['__custom__'] });
    } else {
      onChange({ ...answer, selected: [...answer.selected, '__custom__'] });
    }
  };

  return (
    <div className='flex flex-col gap-2.5'>
      <Label className='text-fg-primary text-sm font-medium'>
        {data.question}
      </Label>

      {qType !== 'text' && options.length > 0 && (
        <div className='flex flex-col gap-1.5'>
          {options.map((option, idx) => {
            const isSelected = answer.selected.includes(option);
            const isRecommended = data.recommended === idx;
            return (
              <Button
                key={option}
                variant='outline'
                className={cn(
                  'h-auto justify-start gap-2.5 px-3 py-2.5 text-sm font-normal',
                  isSelected
                    ? 'border-fg-primary text-fg-primary'
                    : 'border-line-primary text-fg-secondary',
                )}
                onClick={() => handleOptionClick(option)}
              >
                <div
                  className={cn(
                    'flex size-4 shrink-0 items-center justify-center rounded-full border',
                    isSelected
                      ? 'border-fg-primary bg-fg-primary'
                      : 'border-fg-muted',
                  )}
                >
                  {isSelected && (
                    <Check
                      className='text-canvas-primary size-2.5'
                      strokeWidth={3}
                    />
                  )}
                </div>
                <span className='flex-1 text-left text-xs'>{option}</span>
                {isRecommended && (
                  <Badge
                    variant='default'
                    className='shrink-0 text-[10px] font-normal'
                  >
                    추천
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>
      )}

      {qType !== 'text' && allowCustom && (
        <div className='flex flex-col gap-1.5'>
          <Button
            variant='outline'
            className={cn(
              'h-auto justify-start px-3 py-2.5 text-xs font-normal',
              isCustomActive
                ? 'border-fg-primary text-fg-primary'
                : 'border-line-primary text-fg-muted',
            )}
            onClick={handleCustomToggle}
          >
            직접 입력
          </Button>
          {isCustomActive && (
            <Textarea
              value={answer.customText}
              onChange={(e) =>
                onChange({ ...answer, customText: e.target.value })
              }
              placeholder='답변을 입력하세요...'
              rows={2}
              autoFocus
            />
          )}
        </div>
      )}

      {qType === 'text' && (
        <Textarea
          value={answer.customText}
          onChange={(e) => onChange({ ...answer, customText: e.target.value })}
          placeholder='답변을 입력하세요...'
          rows={2}
        />
      )}
    </div>
  );
}

/* ── 유틸리티 ── */

function isQuestionAnswered(data: QuestionData, answer: SingleAnswer): boolean {
  const qType = data.type ?? 'single';
  if (qType === 'text') return answer.customText.trim().length > 0;
  const hasOption = answer.selected.some((s) => s !== '__custom__');
  const hasCustom =
    answer.selected.includes('__custom__') &&
    answer.customText.trim().length > 0;
  return hasOption || hasCustom;
}

function getAnswerSummary(data: QuestionData, answer: SingleAnswer): string {
  const qType = data.type ?? 'single';
  if (qType === 'text') return answer.customText.trim();
  const parts = answer.selected
    .filter((s) => s !== '__custom__')
    .concat(
      answer.selected.includes('__custom__') && answer.customText.trim()
        ? [answer.customText.trim()]
        : [],
    );
  return parts.join(', ');
}

function formatAnswers(questions: QuestionData[], answers: AnswerMap): string {
  return questions
    .map((q, i) => {
      const key = q.id ?? `q${i}`;
      const answer = answers[key] ?? EMPTY_ANSWER;
      return `${i + 1}. ${q.question}: ${getAnswerSummary(q, answer)}`;
    })
    .join('\n');
}

/* ── Questionnaire 메인 ── */

export function Questionnaire({ questions, onSubmit }: QuestionnaireProps) {
  const keys = useMemo(
    () => questions.map((q, i) => q.id ?? `q${i}`),
    [questions],
  );

  const [answers, setAnswers] = useState<AnswerMap>(() => {
    const initial: AnswerMap = {};
    keys.forEach((k) => {
      initial[k] = { ...EMPTY_ANSWER };
    });
    return initial;
  });
  const [activeKey, setActiveKey] = useState<string>(keys[0]);
  const [submitted, setSubmitted] = useState(false);

  const answeredList = questions.map((q, i) =>
    isQuestionAnswered(q, answers[keys[i]] ?? EMPTY_ANSWER),
  );
  const answeredCount = answeredList.filter(Boolean).length;
  const allAnswered = answeredList.every(Boolean);

  const updateAnswer = useCallback((key: string, answer: SingleAnswer) => {
    setAnswers((prev) => ({ ...prev, [key]: answer }));
  }, []);

  const goNext = useCallback(() => {
    setActiveKey((curr) => {
      const i = keys.indexOf(curr);
      return i >= 0 && i < keys.length - 1 ? keys[i + 1] : curr;
    });
  }, [keys]);

  const handleSubmit = () => {
    if (!allAnswered) return;
    setSubmitted(true);
    onSubmit(formatAnswers(questions, answers));
  };

  if (submitted) return null;

  return (
    <div className='border-line-primary bg-canvas-surface w-full overflow-hidden rounded-xl border'>
      <Tabs value={activeKey} onValueChange={setActiveKey} className='gap-0'>
        <div className='border-line-primary px-2 py-1.5'>
          <TabsList
            variant='line'
            className='w-full justify-start overflow-x-auto overflow-y-hidden'
          >
            {questions.map((q, i) => {
              const key = keys[i];
              const answered = answeredList[i];
              const label = q.topic?.trim() || `질문 ${i + 1}`;
              return (
                <TabsTrigger key={key} value={key} className='shrink-0 gap-1.5'>
                  {answered && (
                    <Check
                      className='text-accent-primary size-3'
                      strokeWidth={3}
                    />
                  )}
                  <span className='max-w-40 truncate'>{label}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>
        </div>

        {questions.map((q, i) => {
          const key = keys[i];
          return (
            <TabsContent key={key} value={key} className='p-4'>
              <QuestionItem
                data={q}
                answer={answers[key] ?? EMPTY_ANSWER}
                onChange={(a) => updateAnswer(key, a)}
                onAutoNext={goNext}
              />
            </TabsContent>
          );
        })}
      </Tabs>

      <div className='border-line-primary flex items-center justify-between border-t px-4 py-2.5'>
        <span className='text-fg-muted text-xs'>
          {answeredCount}/{questions.length} 완료
        </span>
        <Button
          size='sm'
          onClick={handleSubmit}
          disabled={!allAnswered}
          className='gap-1.5'
        >
          <Forward className='size-3.5' />
          답변하기
        </Button>
      </div>
    </div>
  );
}
