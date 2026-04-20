"use client";

import { ArtifactPanel } from "@/components/artifacts/ArtifactPanel";
import { SourceViewerPanel } from "@/components/chat/SourceViewerPanel";
import { usePanelStore } from "@/stores/panel-store";
import { AnimatePresence, motion } from "motion/react";

export function RightPanel() {
  const view = usePanelStore((s) => s.rightPanelView);

  return (
    <div className="bg-canvas-primary relative flex h-full flex-col overflow-hidden">
      <AnimatePresence mode="wait" initial={false}>
        {view === "source-viewer" ? (
          <motion.div
            key="source-viewer"
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0, ease: "easeOut" }}
            className="h-full"
          >
            <SourceViewerPanel />
          </motion.div>
        ) : (
          <motion.div
            key="artifacts"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="h-full"
          >
            <ArtifactPanel />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
