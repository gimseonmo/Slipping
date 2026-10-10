import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileUp, RotateCcw, Wifi, WifiOff } from "lucide-react";
import { controlSlideshow, getStatus, uploadPresentation } from "../services/api";
import { usePresentationSocket } from "../hooks/usePresentationSocket";
import type { Presentation, SlideNotes } from "../types/messages";

function slideAt(presentation: Presentation | null, slideNumber: number): SlideNotes | null {
  return presentation?.slides.find((slide) => slide.slideNumber === slideNumber) ?? null;
}

type SlideAction = "next" | "previous" | "first";

function moveLocally(presentation: Presentation | null, action: SlideAction): Presentation | null {
  if (!presentation) return null;
  const offset = action === "next" ? 1 : action === "previous" ? -1 : 0;
  const currentSlide = action === "first" ? 1 : Math.max(1, Math.min(presentation.slideCount, presentation.currentSlide + offset));
  if (currentSlide === presentation.currentSlide) return presentation;
  return {
    ...presentation,
    currentSlide,
    syncMessage: action === "next" ? "다음 슬라이드" : action === "previous" ? "이전 슬라이드" : "첫 슬라이드"
  };
}

export function App() {
  const [presentation, setPresentation] = useState<Presentation | null>(null);
  const [uploading, setUploading] = useState(false);
  const [statusText, setStatusText] = useState("시작 중");
  const workspaceRef = useRef<HTMLElement>(null);
  const swipeStartRef = useRef<{ x: number; y: number; time: number } | null>(null);

  const handlePresentation = useCallback((next: Presentation) => {
    setPresentation(next);
  }, []);
  const socket = usePresentationSocket(handlePresentation);
  const current = slideAt(presentation, presentation?.currentSlide ?? 1);

  useEffect(() => {
    getStatus()
      .then((status) => {
        setPresentation(status.presentation);
        setStatusText(status.hasPresentation ? "발표 자료 준비됨" : "발표 자료 업로드 대기 중");
      })
      .catch((error: Error) => setStatusText(error.message));
  }, []);

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;

    const onNativeTouchStart = (event: TouchEvent) => {
      if (event.touches.length !== 1) return;
      const touch = event.touches[0];
      swipeStartRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
    };

    const onNativeTouchMove = (event: TouchEvent) => {
      const start = swipeStartRef.current;
      if (!start || event.touches.length !== 1) return;
      const touch = event.touches[0];
      const dx = touch.clientX - start.x;
      const dy = touch.clientY - start.y;
      if (Math.abs(dx) > 14 && Math.abs(dx) > Math.abs(dy) * 1.1) {
        event.preventDefault();
      }
    };

    const onNativeTouchEnd = (event: TouchEvent) => {
      const start = swipeStartRef.current;
      swipeStartRef.current = null;
      if (!start || event.changedTouches.length !== 1) return;

      const touch = event.changedTouches[0];
      const dx = touch.clientX - start.x;
      const dy = touch.clientY - start.y;
      const elapsed = Date.now() - start.time;
      const horizontal = Math.abs(dx) >= 56 && Math.abs(dx) > Math.abs(dy) * 1.12;
      if (!horizontal || elapsed > 1200) return;

      event.preventDefault();
      void sendSlideControl(dx < 0 ? "next" : "previous");
    };

    workspace.addEventListener("touchstart", onNativeTouchStart, { passive: true });
    workspace.addEventListener("touchmove", onNativeTouchMove, { passive: false });
    workspace.addEventListener("touchend", onNativeTouchEnd, { passive: false });
    return () => {
      workspace.removeEventListener("touchstart", onNativeTouchStart);
      workspace.removeEventListener("touchmove", onNativeTouchMove);
      workspace.removeEventListener("touchend", onNativeTouchEnd);
    };
  }, []);

  async function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const nextPresentation = await uploadPresentation(file);
      setPresentation(nextPresentation);
      setStatusText("발표 자료를 불러왔습니다");
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "업로드 실패");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function sendSlideControl(action: SlideAction) {
    setPresentation((currentPresentation) => moveLocally(currentPresentation, action));
    setStatusText(action === "next" ? "다음 슬라이드" : action === "previous" ? "이전 슬라이드" : "첫 슬라이드");

    try {
      const nextPresentation = await controlSlideshow(action);
      if (nextPresentation) {
        setPresentation(nextPresentation);
      }
    } catch (error) {
      setStatusText(error instanceof Error ? error.message : "PowerPoint 제어 실패");
    }
  }

  const statusLabel = useMemo(() => {
    if (socket.connection === "disconnected") return "연결 끊김";
    if (socket.connection === "connecting") return "연결 중";
    if (!presentation) return "업로드 대기";
    if (presentation.powerpointConnected) return "PowerPoint 감지됨";
    return "PowerPoint 대기";
  }, [presentation, socket.connection]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="brand">Slipping</p>
          <h1>{presentation?.title ?? "발표 자료를 연결하세요"}</h1>
        </div>
        <div className="topbar-actions">
          <button className="icon-button" onClick={() => void sendSlideControl("first")} title="첫 슬라이드로">
            <RotateCcw size={20} />
          </button>
          <label className="icon-button upload-button" title="PPTX 업로드">
            <FileUp size={20} />
            <input type="file" accept=".pptx" onChange={onUpload} disabled={uploading} />
          </label>
        </div>
      </header>

      <section className="status-row" aria-live="polite">
        <span className={`status-pill ${socket.connection}`}>
          {socket.connection === "disconnected" ? <WifiOff size={16} /> : <Wifi size={16} />}
          {statusLabel}
        </span>
        <span>{socket.message || statusText}</span>
        {presentation && <span>{presentation.currentSlide} / {presentation.slideCount}</span>}
      </section>

      <section ref={workspaceRef} className="workspace">
        <article className="notes-stage">
          {current ? (
            <>
              <div className="slide-meta">
                <span>{current.slideNumber}번</span>
                <strong>{current.title}</strong>
              </div>
              <div className="notes-reader">
                {current.notes.trim() ? current.notes : "이 슬라이드에는 발표자 노트가 없습니다."}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <strong>PPTX를 업로드하면 발표자 노트가 여기에 표시됩니다.</strong>
              <span>iPad에서 좌우로 쓸어 슬라이드를 넘길 수 있습니다.</span>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}
