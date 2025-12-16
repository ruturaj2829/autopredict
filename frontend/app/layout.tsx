import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'AutoPredict – Agentic Predictive Maintenance Demo',
  description: 'Judge-friendly frontend explaining hybrid RF+LSTM, LangGraph orchestration, UEBA, voice AI, and manufacturing RCA/CAPA.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <div className="border-b border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950/90">
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-400/40 text-xs monospace">
                AI
              </span>
              <div>
                <div className="text-sm font-semibold leading-tight">
                  AutoPredict Prototype
                </div>
                <div className="text-[0.7rem] text-slate-400 leading-tight">
                  Hybrid RF+LSTM · LangGraph orchestration · UEBA guard · Voice AI · RCA/CAPA
                </div>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-[0.75rem] text-slate-400">
              <span className="badge badge-pill-strong">Backend: FastAPI</span>
              <span className="badge badge-pill">Frontend: Next.js</span>
            </div>
          </div>
        </div>
        <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}

