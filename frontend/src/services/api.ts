import type { Presentation, StatusResponse } from "../types/messages";

export async function getStatus(): Promise<StatusResponse> {
  const response = await fetch("/api/status");
  if (!response.ok) throw new Error("상태를 불러오지 못했습니다.");
  return response.json();
}

export async function uploadPresentation(file: File): Promise<Presentation> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/presentations/upload", {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "업로드 실패" }));
    throw new Error(error.detail ?? "업로드 실패");
  }
  return response.json();
}

export async function saveNote(slideNumber: number, notes: string): Promise<Presentation> {
  const response = await fetch(`/api/notes/${slideNumber}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes })
  });
  if (!response.ok) throw new Error("노트를 저장하지 못했습니다.");
  return response.json();
}

export async function restoreNote(slideNumber: number): Promise<Presentation> {
  const response = await fetch(`/api/notes/${slideNumber}/restore`, {
    method: "POST"
  });
  if (!response.ok) throw new Error("원본 노트로 복원하지 못했습니다.");
  return response.json();
}

export async function controlSlideshow(action: "next" | "previous" | "first"): Promise<Presentation | null> {
  const response = await fetch(`/api/slideshow/${action}`, {
    method: "POST"
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "PowerPoint 제어 실패" }));
    throw new Error(error.detail ?? "PowerPoint 제어 실패");
  }
  const result = (await response.json()) as { ok: boolean; message?: string; presentation?: Presentation | null };
  if (!result.ok) {
    throw new Error(result.message ?? "PowerPoint 제어 실패");
  }
  return result.presentation ?? null;
}
