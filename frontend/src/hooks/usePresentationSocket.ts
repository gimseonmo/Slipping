import { useEffect, useRef, useState } from "react";
import type { Presentation, ServerMessage } from "../types/messages";

function isPresentation(payload: ServerMessage["payload"]): payload is Presentation {
  return "slides" in payload;
}

export function usePresentationSocket(onPresentation: (presentation: Presentation) => void) {
  const [connection, setConnection] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [message, setMessage] = useState("서버에 연결 중");
  const retryTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let closed = false;

    const connect = () => {
      setConnection("connecting");
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

      socket.onopen = () => {
        setConnection("connected");
        setMessage("연결됨");
        socket?.send(JSON.stringify({ type: "ping" }));
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as ServerMessage;
        if (data.type === "error") {
          setMessage("message" in data.payload ? data.payload.message ?? "오류" : "오류");
          return;
        }
        if (isPresentation(data.payload)) {
          onPresentation(data.payload);
          setMessage(data.payload.syncMessage);
        } else if ("message" in data.payload && data.payload.message) {
          setMessage(data.payload.message);
        }
      };

      socket.onclose = () => {
        if (closed) return;
        setConnection("disconnected");
        setMessage("연결이 끊어졌습니다. 재연결 중");
        retryTimer.current = window.setTimeout(connect, 1200);
      };
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer.current) window.clearTimeout(retryTimer.current);
      socket?.close();
    };
  }, [onPresentation]);

  return { connection, message };
}
