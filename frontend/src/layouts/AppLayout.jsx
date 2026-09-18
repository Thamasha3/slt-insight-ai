import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu } from "lucide-react";
import { ChatProvider } from "../context/ChatContext.jsx";
import Sidebar from "./Sidebar.jsx";

function AppShell() {
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isChat = pathname === "/chat";

  return (
    <div className="flex h-screen overflow-hidden bg-page">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="relative flex min-w-0 flex-1 flex-col bg-page">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="absolute left-3 top-3 z-20 rounded-lg p-2 text-slate-600 hover:bg-white md:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <main className={isChat ? "flex min-h-0 flex-1 flex-col" : "flex-1 overflow-y-auto px-4 py-8 pt-14 md:px-8 md:pt-8"}>
          <div className={isChat ? "flex min-h-0 flex-1 flex-col" : "mx-auto w-full max-w-6xl"}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export default function AppLayout() {
  return (
    <ChatProvider>
      <AppShell />
    </ChatProvider>
  );
}
