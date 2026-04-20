'use client';

import dynamic from 'next/dynamic';
import { use } from 'react';

const ChatArea = dynamic(() => import('@/components/chat/ChatArea').then((m) => m.ChatArea), {
  ssr: false,
});

export default function AgentPage({
  params,
}: {
  params: Promise<{ sessionId?: string[] }>;
}) {
  const { sessionId } = use(params);
  return <ChatArea sessionId={sessionId?.[0]} />;
}
