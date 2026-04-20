import { Skeleton } from '@/components/ui/skeleton';

export function ProjectListSkeleton() {
  return (
    <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className='border-line-primary rounded-lg border p-5'>
          <div className='mb-3 flex items-center gap-2.5'>
            <Skeleton className='size-9 rounded-md' />
            <div className='flex flex-col gap-1.5'>
              <Skeleton className='h-4 w-32' />
              <Skeleton className='h-3 w-20' />
            </div>
          </div>
          <Skeleton className='mb-3 h-4 w-full' />
          <div className='mb-3 flex gap-1.5'>
            <Skeleton className='h-5 w-20 rounded-full' />
            <Skeleton className='h-5 w-16 rounded-full' />
          </div>
          <div className='flex gap-4'>
            <Skeleton className='h-3 w-24' />
            <Skeleton className='h-3 w-12' />
          </div>
        </div>
      ))}
    </div>
  );
}
