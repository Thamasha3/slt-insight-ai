import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api.js";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [queuedPrompt, setQueuedPrompt] = useState(null);

  const loadSessions = useCallback(async () => {
    try {
      const response = await api.get("/chat/sessions");
      setSessions(response.data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  function startNewChat() {
    setSessionId(null);
    navigate("/chat");
  }

  function queuePrompt(text) {
    setSessionId(null);
    setQueuedPrompt(text);
    navigate("/chat");
  }

  function consumeQueuedPrompt() {
    const next = queuedPrompt;
    setQueuedPrompt(null);
    return next;
  }

  return (
    <ChatContext.Provider
      value={{
        sessions,
        sessionId,
        setSessionId,
        loadSessions,
        startNewChat,
        queuedPrompt,
        queuePrompt,
        consumeQueuedPrompt,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const value = useContext(ChatContext);
  if (!value) {
    throw new Error("useChat must be used inside ChatProvider");
  }
  return value;
}
