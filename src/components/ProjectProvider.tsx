"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { ProjectState, DEFAULT_PROJECT } from "@/lib/api";

interface ProjectContextType {
  project: ProjectState;
  update: (partial: Partial<ProjectState>) => void;
  reset: () => void;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [project, setProject] = useState<ProjectState>(DEFAULT_PROJECT);

  const update = useCallback((partial: Partial<ProjectState>) => {
    setProject((prev) => ({ ...prev, ...partial }));
  }, []);

  const reset = useCallback(() => setProject(DEFAULT_PROJECT), []);

  return (
    <ProjectContext.Provider value={{ project, update, reset }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within ProjectProvider");
  return ctx;
}
