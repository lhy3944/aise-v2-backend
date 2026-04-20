import { Skeleton } from '@/components/ui/skeleton';

interface ListSkeletonProps {
  /** Number of row skeletons to render */
  rows?: number;
  /** Height class for each row (e.g. 'h-10', 'h-12') */
  rowHeight?: string;
  /** Whether to show a header skeleton above the rows */
  header?: boolean;
  /** Height class for the header skeleton */
  headerHeight?: string;
}

export function ListSkeleton({
  rows = 5,
  rowHeight = 'h-8',
  header = true,
  headerHeight = 'h-10',
}: ListSkeletonProps) {
  return (
    <div className='flex flex-col gap-8'>
      {header && <Skeleton className={`${headerHeight} w-full rounded-md`} />}

      <div className='flex flex-col gap-2'>
        {Array.from({ length: rows - 1 }).map((_, i) => (
          <Skeleton key={i} className={`${rowHeight} w-full rounded-md`} />
        ))}
      </div>
    </div>
  );
}
