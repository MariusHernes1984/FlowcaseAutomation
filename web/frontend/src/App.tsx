import { Link, Route, Routes } from "react-router-dom";

import HomePage from "@/pages/HomePage";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
        <nav className="mx-auto flex max-w-6xl items-center justify-between">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Flowcase
          </Link>
          <div className="text-sm text-slate-500">v0.1 — scaffolding</div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </main>
      <footer className="border-t border-slate-200 bg-white px-6 py-4 text-center text-xs text-slate-500">
        Atea Flowcase · agent-drevet konsulent-søk
      </footer>
    </div>
  );
}
