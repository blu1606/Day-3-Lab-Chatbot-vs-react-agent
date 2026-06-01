"use client";

import {
  Wrench,
  CheckCircle2,
  ShieldAlert,
  Bot,
  Clock3,
} from "lucide-react";
import { traces, type AgentTrace, type TraceStep } from "@/lib/mock-traces";

const stepIcons = {
  thought: Bot,
  tool: Wrench,
  observation: CheckCircle2,
  final: CheckCircle2,
  error: ShieldAlert,
};

export function TraceRailInteractive({
  activeSessionId,
  customTrace,
}: {
  activeSessionId: string;
  customTrace?: any;
}) {
  // Retrieve current active trace details
  const activeTrace: AgentTrace = (() => {
    if (customTrace) {
      return customTrace;
    }
    if (activeSessionId === "session-security") {
      return traces.find((t) => t.id === "security-blocked") || traces[1];
    }
    if (activeSessionId === "session-student") {
      return traces.find((t) => t.id === "timeout-fallback") || traces[2];
    }
    return traces[0]; // success-cohort-diagnostic
  })();

  return (
    <aside className="flex flex-col rounded-2xl border border-[rgba(11,9,7,0.12)] bg-[#fffcf6] p-4 shadow-sm lg:min-h-0 lg:overflow-auto">
      <div className="mb-4 flex items-start justify-between gap-3 border-b border-[rgba(11,9,7,0.08)] pb-3">
        <div>
          <h2 className="text-sm font-bold text-[#3c3a39]">Trace telemetry</h2>
          <p className="mt-1 font-mono text-[10px] text-[rgba(11,9,7,0.5)]">
            /langsmith-run-details
          </p>
        </div>
        <Clock3 className="size-4 text-[rgba(11,9,7,0.4)]" />
      </div>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <Metric label="Latency" value={`${activeTrace.latencyMs}ms`} warning={activeTrace.latencyMs > 5000} />
        <Metric label="Prompt" value={String(activeTrace.promptTokens)} />
        <Metric label="Output" value={String(activeTrace.completionTokens)} />
      </div>

      <div className="rounded-xl border border-[rgba(11,9,7,0.08)] bg-[#fefcf5] p-3 mb-4">
        <p className="font-mono text-[10px] uppercase tracking-wider text-[#817fff] font-bold">
          /telemetry-summary
        </p>
        <p className="mt-2 text-sm leading-6 text-[#3c3a39] font-medium">{activeTrace.summary}</p>
      </div>

      <div className="space-y-2.5">
        <p className="font-mono text-[10px] uppercase tracking-wider text-[#ff7300] font-bold">
          /mini-trace-steps
        </p>
        {activeTrace.steps.map((step, index) => (
          <TraceMiniStep index={index + 1} key={step.id} step={step} />
        ))}
      </div>
    </aside>
  );
}

function Metric({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string;
  warning?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-2.5 bg-[#fefcf5] ${
        warning ? "border-[#ff272d]/30 bg-[#ff272d]/5 text-[#ff272d]" : "border-[rgba(11,9,7,0.06)]"
      }`}
    >
      <p className="font-mono text-[9px] uppercase tracking-wider text-[rgba(11,9,7,0.4)]">/{label.toLowerCase()}</p>
      <p className={`mt-1 text-xs font-semibold ${warning ? "text-[#ff272d]" : "text-[#3c3a39]"}`}>{value}</p>
    </div>
  );
}

function TraceMiniStep({ step, index }: { step: TraceStep; index: number }) {
  const Icon = stepIcons[step.kind] || Wrench;

  return (
    <div className="rounded-xl border border-[rgba(11,9,7,0.06)] bg-[#fefcf5] p-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-[rgba(11,9,7,0.1)] bg-[#fffcf6] text-xs text-[#3c3a39] font-mono">
          {index}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <Icon className="size-3.5 text-[rgba(11,9,7,0.4)]" />
            <p className="truncate text-sm font-semibold text-[#3c3a39]">{step.title}</p>
          </div>
          <p className="line-clamp-2 text-xs leading-5 text-[rgba(11,9,7,0.5)]">{step.content}</p>
          <div className="mt-2">
            {step.errorCode ? (
              <span className="rounded-full border border-[#ff272d]/30 bg-[#ff272d]/10 px-2 py-0.5 text-[9px] text-[#ff272d] font-semibold">
                {step.errorCode}
              </span>
            ) : (
              <span className="rounded-full border border-[#22c55e]/30 bg-[#22c55e]/10 px-2 py-0.5 text-[9px] text-[#22c55e] font-semibold animate-pulse">
                completed · {step.durationMs || 100}ms
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
