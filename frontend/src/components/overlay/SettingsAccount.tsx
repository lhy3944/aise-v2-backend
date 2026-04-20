'use client';

import { Camera, Mail, Building2, Briefcase, Phone, Shield } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

export function SettingsAccount() {
  return (
    <div className='flex flex-col gap-6'>
      {/* 프로필 섹션 */}
      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>프로필</h3>
        <div className='flex items-center gap-4'>
          <div className='relative'>
            <Avatar className='h-16 w-16'>
              <AvatarFallback className='bg-canvas-surface text-fg-primary text-xl font-medium'>
                A
              </AvatarFallback>
            </Avatar>
            <button
              type='button'
              className='bg-canvas-surface border-line-primary text-fg-secondary hover:text-fg-primary absolute -right-1 -bottom-1 flex h-6 w-6 items-center justify-center rounded-full border shadow-sm transition-colors'
            >
              <Camera className='h-3 w-3' />
            </button>
          </div>
          <div className='flex flex-col gap-1'>
            <span className='text-fg-primary text-base font-medium'>Admin User</span>
            <span className='text-fg-muted text-xs'>SSO 계정으로 연동됨</span>
          </div>
        </div>
      </div>

      <Separator />

      {/* 계정 정보 */}
      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>계정 정보</h3>
        <div className='flex flex-col gap-4'>
          <div className='flex flex-col gap-1.5'>
            <Label className='text-fg-secondary flex items-center gap-1.5 text-sm'>
              <Mail className='h-3.5 w-3.5' />
              이메일
            </Label>
            <Input value='admin@aise.com' disabled className='bg-canvas-secondary/50' />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label className='text-fg-secondary flex items-center gap-1.5 text-sm'>
              <Building2 className='h-3.5 w-3.5' />
              소속
            </Label>
            <Input value='공학연구소' disabled className='bg-canvas-secondary/50' />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label className='text-fg-secondary flex items-center gap-1.5 text-sm'>
              <Briefcase className='h-3.5 w-3.5' />
              부서
            </Label>
            <Input value='SW개발팀' disabled className='bg-canvas-secondary/50' />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label className='text-fg-secondary flex items-center gap-1.5 text-sm'>
              <Phone className='h-3.5 w-3.5' />
              연락처
            </Label>
            <Input value='010-1234-5678' disabled className='bg-canvas-secondary/50' />
          </div>
        </div>
      </div>

      <Separator />

      {/* 보안 */}
      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>보안</h3>
        <div className='flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <div className='flex flex-col gap-0.5'>
              <Label className='text-fg-secondary flex items-center gap-1.5 text-sm'>
                <Shield className='h-3.5 w-3.5' />
                인증 방식
              </Label>
              <span className='text-fg-muted text-xs'>Keycloak SSO를 통해 인증됩니다</span>
            </div>
            <Badge variant='outline' className='text-fg-secondary'>
              SSO
            </Badge>
          </div>
          <div className='flex items-center justify-between'>
            <div className='flex flex-col gap-0.5'>
              <span className='text-fg-secondary text-sm'>비밀번호 변경</span>
              <span className='text-fg-muted text-xs'>SSO 포털에서 변경할 수 있습니다</span>
            </div>
            <Button variant='outline' size='sm' disabled>
              SSO 포털로 이동
            </Button>
          </div>
        </div>
      </div>

      <Separator />

      {/* 세션 */}
      <div>
        <h3 className='text-fg-primary mb-4 text-sm font-semibold'>세션</h3>
        <div className='flex items-center justify-between'>
          <div className='flex flex-col gap-0.5'>
            <span className='text-fg-secondary text-sm'>모든 기기에서 로그아웃</span>
            <span className='text-fg-muted text-xs'>현재 세션을 포함한 모든 활성 세션이 종료됩니다</span>
          </div>
          <Button variant='outline' size='sm' disabled>
            전체 로그아웃
          </Button>
        </div>
      </div>
    </div>
  );
}
