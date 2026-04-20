"use client";

import { cn } from "@/lib/utils";
import { useProjectStore } from "@/stores/project-store";
import { useReadinessStore } from "@/stores/readiness-store";
import { BookOpen, FolderOpen, LayoutList } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const ITEMS = [
  { key: "knowledge" as const, icon: FolderOpen },
  { key: "glossary" as const, icon: BookOpen },
  { key: "sections" as const, icon: LayoutList },
];

export function ReadinessMiniView() {
  const router = useRouter();
  const currentProject = useProjectStore((s) => s.currentProject);
  const data = useReadinessStore((s) => s.data);
  const fetch = useReadinessStore((s) => s.fetch);

  useEffect(() => {
    if (currentProject) {
      fetch(currentProject.project_id);
    }
  }, [currentProject, fetch]);

  if (!currentProject || !data) return null;

  return (
    <div
      className="border-line-primary hover:bg-canvas-surface/50 flex cursor-pointer items-center justify-between rounded-md border px-2.5 py-2.5 transition-colors"
      onClick={() => router.push(`/projects/${currentProject.project_id}`)}
    >
      {ITEMS.map(({ key, icon: Icon }) => {
        const item = data[key];
        return (
          <div key={key} className="flex items-center gap-1">
            <Icon className={cn("size-4")} strokeWidth={1.5} />
            <span className={cn("text-xs")}>{item.count}</span>
          </div>
        );
      })}
      <span
        className={cn(
          "size-2 rounded-full mr-1",
          data.is_ready ? "bg-green-500" : "bg-amber-500",
        )}
      />
    </div>
  );
}
