"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Activity,
  BookOpen,
  ChevronDown,
  ChevronRight,
  GraduationCap,
  ListTodo,
  TrendingUp,
  User,
  Users,
  MessageSquare,
  FileText,
  PlusCircle,
  Clock,
  Sparkles,
  Award,
  PanelRight,
} from "lucide-react";
import type { Student, StudentGroup, CohortSummary } from "@/lib/types";
import { mockReports, type DiagnosticReportVersion } from "@/lib/mock-reports";
import { SidebarUnified } from "@/components/sidebar-unified";

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [groups, setGroups] = useState<StudentGroup[]>([]);
  const [cohort, setCohort] = useState<CohortSummary | null>(null);
  
  const [selectedStudentId, setSelectedStudentId] = useState<string>("STU001");
  const [reportsList, setReportsList] = useState<DiagnosticReportVersion[]>(mockReports);
  const [selectedReportIdx, setSelectedReportIdx] = useState<number>(0);
  
  const [leftNavMode, setLeftNavMode] = useState<"students" | "reports">("students");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [showRightPanel, setShowRightPanel] = useState(true);

  // Resize states
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [subWidth, setSubWidth] = useState(260);
  const [rightPanelWidth, setRightPanelWidth] = useState(340);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [isResizingSub, setIsResizingSub] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);

  const startResizeSidebar = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingSidebar(true);
  };

  const startResizeSub = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingSub(true);
  };

  const startResizeRight = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingRight(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingSidebar) {
        const newWidth = Math.max(180, Math.min(450, e.clientX - 16));
        setSidebarWidth(newWidth);
      }
      if (isResizingSub) {
        const currentSidebar = isCollapsed ? 72 : sidebarWidth;
        const newWidth = Math.max(180, Math.min(400, e.clientX - currentSidebar - 24));
        setSubWidth(newWidth);
      }
      if (isResizingRight) {
        const newWidth = Math.max(240, Math.min(550, window.innerWidth - e.clientX - 16));
        setRightPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizingSidebar(false);
      setIsResizingSub(false);
      setIsResizingRight(false);
    };

    if (isResizingSidebar || isResizingSub || isResizingRight) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingSidebar, isResizingSub, isResizingRight, sidebarWidth, isCollapsed]);

  // Listen to tab query changes dynamically to switch views
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "reports") {
        setLeftNavMode("reports");
      } else if (tabParam === "class") {
        setLeftNavMode("reports"); // Map class to reports summary
      } else {
        setLeftNavMode("students");
      }
    }
  }, []);

  useEffect(() => {
    async function load() {
      const [studentsRes, groupsRes, cohortRes] = await Promise.all([
        fetch("/api/students"),
        fetch("/api/student-groups"),
        fetch("/api/cohort"),
      ]);
      setStudents(await studentsRes.json());
      setGroups(await groupsRes.json());
      setCohort(await cohortRes.json());
    }
    load();
  }, []);

  const activeStudent = students.find((s) => s.student_id === selectedStudentId);
  const activeReport = reportsList[selectedReportIdx];

  // Request Gen Report Simulation (Creates v3)
  const handleRequestGenReport = () => {
    if (isGenerating) return;
    setIsGenerating(true);

    setTimeout(() => {
      const newVersion: DiagnosticReportVersion = {
        version: `v${reportsList.length + 1} (Generated)`,
        date: new Date().toISOString().split("T")[0],
        averageScore: 78,
        completionRate: 88,
        atRiskCount: 1,
        totalStudents: 8,
        weakConcepts: [
          { concept: "agentic_loops", score: 68, weakPercent: 38 },
          { concept: "reasoning", score: 71, weakPercent: 25 },
          { concept: "tool_use", score: 82, weakPercent: 12 },
        ],
        groups: [
          {
            name: "Needs Foundation",
            reason: "Học viên cần củng cố nền tảng cơ bản.",
            studentCount: 1,
            actions: [
              "Hỗ trợ chuyên sâu về evaluation và prompting.",
              "Luyện tập 1-1 hàng tuần.",
            ],
          },
          {
            name: "Needs Practice",
            reason: "Học viên cần thực hành nâng cao.",
            studentCount: 3,
            actions: [
              "Giao thêm 3 mini-project thực tế.",
            ],
          },
          {
            name: "Ready for Advanced",
            reason: "Học viên xuất sắc, sẵn sàng nghiên cứu.",
            studentCount: 4,
            actions: [
              "Mời làm trợ giảng hỗ trợ các bạn khác.",
              "Tham gia viết agentic core framework.",
            ],
          },
        ],
      };

      setReportsList([newVersion, ...reportsList]);
      setSelectedReportIdx(0);
      setLeftNavMode("reports");
      setIsGenerating(false);
      
      setSuccessToast("New Diagnostic Report generated successfully!");
      setTimeout(() => setSuccessToast(null), 4000);
    }, 1800);
  };

  const getStudentGroup = (id: string) =>
    groups.find((g) => g.students.some((s) => s.student_id === id));

  return (
    <main className={`mx-auto flex min-h-dvh w-full max-w-[1600px] flex-col gap-4 px-4 py-4 lg:h-dvh lg:overflow-hidden bg-[#f2efe4] ${
      isResizingSidebar || isResizingSub || isResizingRight ? "select-none" : ""
    }`}>
      {/* Toast Alert */}
      {successToast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl bg-[#3c3a39] text-[#fefcf5] border border-emerald-400 px-4 py-3 text-sm font-semibold shadow-lg animate-bounce">
          <Sparkles className="size-4 text-emerald-400 animate-spin" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Header */}
      <header className="flex items-center justify-between rounded-2xl border border-transparent bg-[#3c3a39] px-6 py-4 shadow-md">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-[#ff7300]">
            /gaptutor-mentor-terminal
          </p>
          <h1 className="mt-1 text-xl font-bold tracking-tight text-[#fefcf5] md:text-2xl">
            Cohort Directory & Diagnostics Registry
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/u/0/app"
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 font-mono text-xs text-[#eaeae2] hover:bg-white/10 hover:text-white transition-all shadow-sm"
          >
            <MessageSquare className="size-4 text-[#79deeb]" />
            /back-to-chat
          </Link>
          <button
            onClick={() => setShowRightPanel(!showRightPanel)}
            className="flex size-8 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[#eaeae2] hover:bg-white/10 hover:text-white transition-all shadow-sm"
            title={showRightPanel ? "Collapse right panel" : "Expand right panel"}
            type="button"
          >
            <PanelRight className={`size-4 ${showRightPanel ? "text-[#79deeb]" : "text-neutral-400"}`} />
          </button>
        </div>
      </header>

      {/* Main Collapsible Layout */}
      <section className="flex min-h-0 flex-1 gap-1 transition-all duration-300">
        {/* COLUMN 1: COLLAPSIBLE UNIFIED SIDEBAR */}
        <div style={{ width: isCollapsed ? 72 : sidebarWidth }} className="flex shrink-0 h-full">
          <SidebarUnified
            isCollapsed={isCollapsed}
            onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
            onNewChat={() => {
              window.location.href = "/u/0/app";
            }}
          />
        </div>

        {/* Resizer for Left Sidebar */}
        {!isCollapsed && (
          <div
            onMouseDown={startResizeSidebar}
            className={`w-2 hover:bg-[#ff7300]/20 active:bg-[#ff7300]/40 cursor-col-resize transition-colors flex items-center justify-center shrink-0 rounded-md ${
              isResizingSidebar ? "bg-[#ff7300]/30" : ""
            }`}
            title="Drag to resize sidebar"
          >
            <div className="w-[1px] h-8 bg-[rgba(11,9,7,0.12)]" />
          </div>
        )}

        {/* Cột phụ: Chọn hiển thị danh sách Học sinh hoặc Báo cáo dựa trên leftNavMode */}
        <aside
          style={{ width: subWidth }}
          className="flex flex-col rounded-2xl border border-[rgba(11,9,7,0.12)] bg-[#fffcf6] shadow-sm lg:min-h-0 shrink-0"
        >
          <div className="p-2.5 border-b border-[rgba(11,9,7,0.12)] bg-[#fffcf6]">
            <div className="grid grid-cols-2 gap-1.5 rounded-xl bg-[#fefcf5] border border-[rgba(11,9,7,0.06)] p-1">
              <button
                className={`py-1.5 text-xs font-bold rounded-lg border transition-all ${
                  leftNavMode === "students"
                    ? "bg-[#3c3a39] text-[#fefcf5] border-[#3c3a39] shadow-sm"
                    : "text-[rgba(11,9,7,0.5)] border-transparent hover:text-[#3c3a39] hover:bg-[#eaeae2]/30"
                }`}
                onClick={() => setLeftNavMode("students")}
                type="button"
              >
                Students
              </button>
              <button
                className={`py-1.5 text-xs font-bold rounded-lg border transition-all ${
                  leftNavMode === "reports"
                    ? "bg-[#3c3a39] text-[#fefcf5] border-[#3c3a39] shadow-sm"
                    : "text-[rgba(11,9,7,0.5)] border-transparent hover:text-[#3c3a39] hover:bg-[#eaeae2]/30"
                }`}
                onClick={() => setLeftNavMode("reports")}
                type="button"
              >
                Diag Reports
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-3">
            {leftNavMode === "students" ? (
              <div className="space-y-4">
                {groups.map((group) => {
                  const grpStudents = students.filter((s) =>
                    group.students.some((gs) => gs.student_id === s.student_id)
                  );

                  const groupAccent: Record<string, string> = {
                    "Needs Foundation": "text-[#ff272d]",
                    "Needs Practice": "text-[#ff7300]",
                    "Ready for Advanced": "text-[#22c55e]",
                  };

                  return (
                    <div key={group.group_name} className="space-y-1.5">
                      <p className={`font-mono text-[9px] font-bold uppercase tracking-wider ${groupAccent[group.group_name] || "text-[#3c3a39]"}`}>
                        /{group.group_name.toLowerCase().replace(" ", "-")}
                      </p>
                      <div className="space-y-1">
                        {grpStudents.map((student) => (
                          <button
                            key={student.student_id}
                            className={`w-full flex items-center justify-between rounded-xl border p-2.5 text-left transition-all ${
                              selectedStudentId === student.student_id
                                ? "border-[#3c3a39] bg-[#eaeae2]/40"
                                : "border-[rgba(11,9,7,0.04)] bg-[#fefcf5] hover:border-[rgba(11,9,7,0.1)] hover:bg-[#eaeae2]/10"
                            }`}
                            onClick={() => setSelectedStudentId(student.student_id)}
                            type="button"
                          >
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-[#3c3a39] truncate">
                                {student.name}
                              </p>
                              <p className="text-[10px] text-[rgba(11,9,7,0.5)] mt-0.5">
                                Score: {student.lab_score} · {student.background}
                              </p>
                            </div>
                            <ChevronRight className="size-3.5 text-[rgba(11,9,7,0.4)]" />
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="font-mono text-[9px] font-bold uppercase tracking-wider text-[#817fff]">
                  /report-versions
                </p>
                {reportsList.map((rep, idx) => (
                  <button
                    key={rep.version}
                    className={`w-full text-left rounded-xl border p-3 transition-all ${
                      selectedReportIdx === idx
                        ? "border-[#3c3a39] bg-[#eaeae2]/40"
                        : "border-[rgba(11,9,7,0.04)] bg-[#fefcf5] hover:border-[rgba(11,9,7,0.1)] hover:bg-[#eaeae2]/10"
                    }`}
                    onClick={() => {
                      setSelectedReportIdx(idx);
                    }}
                    type="button"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#3c3a39]">{rep.version}</span>
                      <span className="font-mono text-[9px] text-[rgba(11,9,7,0.4)]">{rep.date}</span>
                    </div>
                    <p className="text-[10px] text-[rgba(11,9,7,0.5)] mt-1 truncate">
                      Avg: {rep.averageScore} · Completion: {rep.completionRate}%
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Resizer for Sub Sidebar */}
        <div
          onMouseDown={startResizeSub}
          className={`w-2 hover:bg-[#ff7300]/20 active:bg-[#ff7300]/40 cursor-col-resize transition-colors flex items-center justify-center shrink-0 rounded-md ${
            isResizingSub ? "bg-[#ff7300]/30" : ""
          }`}
          title="Drag to resize list panel"
        >
          <div className="w-[1px] h-8 bg-[rgba(11,9,7,0.12)]" />
        </div>

        {/* COLUMN 2: CENTER WORKSPACE (Details block viewer) */}
        <section className="flex-1 flex flex-col rounded-2xl border border-[rgba(11,9,7,0.12)] bg-[#fffcf6] shadow-sm lg:min-h-0 overflow-auto p-5 space-y-5">
          {leftNavMode === "students" && activeStudent ? (
            <div className="space-y-5">
              {/* Student basic profile card */}
              <div className="rounded-xl border border-[rgba(11,9,7,0.1)] bg-[#fefcf5] p-5 shadow-xs flex items-center justify-between">
                <div>
                  <span className="font-mono text-[10px] font-bold text-[#ff7300] uppercase tracking-wider">
                    /student-profile
                  </span>
                  <h2 className="text-xl font-bold text-[#3c3a39] mt-1">{activeStudent.name}</h2>
                  <p className="text-xs text-[rgba(11,9,7,0.5)] mt-1">
                    ID: {activeStudent.student_id} · Background: {activeStudent.background}
                  </p>
                </div>
                <div className="rounded-xl bg-[#eaeae2] border border-[rgba(11,9,7,0.08)] px-4 py-2 text-center">
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-[rgba(11,9,7,0.5)]">
                    Lab Score
                  </span>
                  <span className="text-xl font-bold text-[#3c3a39]">{activeStudent.lab_score}</span>
                </div>
              </div>

              {/* Grid detail blocks */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Concept Mastery Block */}
                <div className="rounded-xl border border-[rgba(11,9,7,0.08)] bg-[#fffcf6] p-4 shadow-sm space-y-3">
                  <p className="font-mono text-[10px] font-bold text-[#817fff] uppercase tracking-wider">
                    /concept-mastery-scores
                  </p>
                  <div className="space-y-2">
                    {Object.entries(activeStudent.concept_mastery).map(([concept, val]) => (
                      <div key={concept} className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold text-[#3c3a39]">
                          <span className="capitalize">{concept.replace("_", " ")}</span>
                          <span>{val}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-[#eaeae2] overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              concept === "agentic_loops"
                                ? "bg-[#ff7300]"
                                : concept === "reasoning"
                                ? "bg-[#817fff]"
                                : concept === "tool_use"
                                ? "bg-[#2677ff]"
                                : concept === "evaluation"
                                ? "bg-[#f49eff]"
                                : "bg-[#ffc753]"
                            }`}
                            style={{ width: `${val}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Performance & Cohort Alignment Block */}
                <div className="space-y-4">
                  <div className="rounded-xl border border-[rgba(11,9,7,0.08)] bg-[#fffcf6] p-4 shadow-sm">
                    <p className="font-mono text-[10px] font-bold text-[#2677ff] uppercase tracking-wider">
                      /cohort-alignment
                    </p>
                    <div className="mt-3 flex items-center justify-between border-b border-[rgba(11,9,7,0.06)] pb-2.5">
                      <span className="text-xs text-[rgba(11,9,7,0.5)]">Diagnostic Score</span>
                      <span className="text-sm font-bold text-[#3c3a39]">{activeStudent.diagnostic_score}</span>
                    </div>
                    <div className="mt-2.5 flex items-center justify-between border-b border-[rgba(11,9,7,0.06)] pb-2.5">
                      <span className="text-xs text-[rgba(11,9,7,0.5)]">Activity Level</span>
                      <span className="text-xs font-mono font-bold text-[#22c55e] uppercase">
                        {activeStudent.activity_level}
                      </span>
                    </div>
                    <div className="mt-2.5 flex items-center justify-between">
                      <span className="text-xs text-[rgba(11,9,7,0.5)]">Variant Q Status</span>
                      <span className={`text-xs font-mono font-bold uppercase ${
                        activeStudent.variant_question_result === "correct"
                          ? "text-[#22c55e]"
                          : "text-[#ff272d]"
                      }`}>
                        {activeStudent.variant_question_result}
                      </span>
                    </div>
                  </div>

                  {getStudentGroup(activeStudent.student_id) && (
                    <div className="rounded-xl border border-[rgba(11,9,7,0.08)] bg-[#fffcf6] p-4 shadow-sm flex gap-3">
                      <BookOpen className="size-4 shrink-0 text-[#2677ff]" />
                      <div>
                        <h4 className="text-xs font-bold text-[#2677ff]">
                          {getStudentGroup(activeStudent.student_id)?.group_name}
                        </h4>
                        <p className="text-[11px] leading-4 text-[rgba(11,9,7,0.5)] mt-1">
                          {getStudentGroup(activeStudent.student_id)?.reason}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Student Journal Activity Log */}
              <div className="rounded-xl border border-[rgba(11,9,7,0.08)] bg-[#fffcf6] p-4 shadow-sm flex gap-3">
                <Activity className="size-4 shrink-0 text-[rgba(11,9,7,0.4)]" />
                <div>
                  <p className="font-mono text-[9px] font-bold text-[rgba(11,9,7,0.4)] uppercase">
                    /journey-log
                  </p>
                  <p className="text-xs leading-5 text-[rgba(11,9,7,0.65)] mt-1">
                    {activeStudent.journey_log}
                  </p>
                </div>
              </div>
            </div>
          ) : activeReport ? (
            <div className="space-y-5">
              {/* Daily report metrics summary */}
              <div className="rounded-xl border border-[rgba(11,9,7,0.12)] bg-[#fefcf5] p-5 shadow-xs">
                <div className="flex items-center justify-between border-b border-[rgba(11,9,7,0.08)] pb-3">
                  <div>
                    <span className="font-mono text-[10px] font-bold text-[#817fff] uppercase tracking-wider">
                      /cohort-diagnostics-report
                    </span>
                    <h2 className="text-lg font-bold text-[#3c3a39] mt-0.5">
                      Diagnostic Session - {activeReport.date}
                    </h2>
                  </div>
                  <span className="rounded-full bg-[#3c3a39] text-[#fefcf5] px-2.5 py-1 text-xs font-mono font-bold">
                    {activeReport.version}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-3 mt-4">
                  <ReportStat label="Avg Score" value={String(activeReport.averageScore)} />
                  <ReportStat label="Completion Rate" value={`${activeReport.completionRate}%`} />
                  <ReportStat label="At Risk" value={String(activeReport.atRiskCount)} highlight />
                  <ReportStat label="Total Cohort" value={String(activeReport.totalStudents)} />
                </div>
              </div>

              {/* Detailed Grouping remediation plans */}
              <div className="space-y-4">
                <p className="font-mono text-[10px] font-bold text-[#ff7300] uppercase tracking-wider">
                  /remediation-actions-mapping
                </p>
                <div className="grid md:grid-cols-2 gap-4">
                  {activeReport.groups.map((grp) => {
                    const borderColors: Record<string, string> = {
                      "Needs Foundation": "border-[#ff272d]/20 bg-[#ff272d]/[0.02]",
                      "Needs Practice": "border-[#ff7300]/20 bg-[#ff7300]/[0.02]",
                      "Ready for Advanced": "border-[#22c55e]/20 bg-[#22c55e]/[0.02]",
                    };
                    const textColors: Record<string, string> = {
                      "Needs Foundation": "text-[#ff272d]",
                      "Needs Practice": "text-[#ff7300]",
                      "Ready for Advanced": "text-[#22c55e]",
                    };

                    return (
                      <div
                        key={grp.name}
                        className={`rounded-xl border p-4 shadow-sm space-y-3 ${
                          borderColors[grp.name] || "border-[rgba(11,9,7,0.08)]"
                        }`}
                      >
                        <div className="flex items-center justify-between border-b border-[rgba(11,9,7,0.06)] pb-2">
                          <h4 className={`text-xs font-bold ${textColors[grp.name] || "text-[#3c3a39]"}`}>
                            {grp.name}
                          </h4>
                          <span className="text-[10px] text-[rgba(11,9,7,0.5)] font-mono font-medium">
                            {grp.studentCount} students
                          </span>
                        </div>
                        <p className="text-[11px] leading-4 text-[rgba(11,9,7,0.5)]">
                          {grp.reason}
                        </p>
                        <div className="space-y-1.5">
                          <p className="font-mono text-[8px] font-bold text-[rgba(11,9,7,0.4)] uppercase flex items-center gap-1">
                            <ListTodo className="size-3" /> /actions
                          </p>
                          <ul className="pl-3 list-disc text-[10px] text-[rgba(11,9,7,0.65)] space-y-1 leading-4">
                            {grp.actions.map((act, idx) => (
                              <li key={idx}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-neutral-500">Select an item from the sidebar.</p>
          )}
        </section>

        {/* Resizer for Right Panel */}
        {showRightPanel && (
          <div
            onMouseDown={startResizeRight}
            className={`w-2 hover:bg-[#ff7300]/20 active:bg-[#ff7300]/40 cursor-col-resize transition-colors flex items-center justify-center shrink-0 rounded-md ${
              isResizingRight ? "bg-[#ff7300]/30" : ""
            }`}
            title="Drag to resize operations panel"
          >
            <div className="w-[1px] h-8 bg-[rgba(11,9,7,0.12)]" />
          </div>
        )}

        {/* COLUMN 3: RIGHT PANEL (Request Gen Report Engine) */}
        {showRightPanel && (
          <aside style={{ width: rightPanelWidth }} className="flex flex-col gap-4 lg:min-h-0 shrink-0">
            {/* Action trigger card */}
            <div className="rounded-2xl border border-[rgba(11,9,7,0.12)] bg-[#fffcf6] p-4 shadow-sm space-y-4">
              <div>
                <span className="font-mono text-[9px] font-bold text-[#ff272d] uppercase tracking-wider">
                  /operations-engine
                </span>
                <h3 className="text-sm font-bold text-[#3c3a39] mt-0.5">Cohort Analysis Terminal</h3>
                <p className="text-[11px] text-[rgba(11,9,7,0.5)] leading-4 mt-1">
                  Kích hoạt phân tích AI telemetry và sinh báo cáo chẩn đoán phiên bản mới nhất theo thời gian thực.
                </p>
              </div>

              <button
                onClick={handleRequestGenReport}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#3c3a39] text-[#fefcf5] hover:opacity-90 transition-opacity py-3 text-xs font-mono font-bold shadow-md disabled:opacity-40"
                type="button"
              >
                {isGenerating ? (
                  <>
                    <Clock className="size-4 animate-spin text-[#79deeb]" />
                    <span>/telemetry-scanning...</span>
                  </>
                ) : (
                  <>
                    <PlusCircle className="size-4 text-[#ffc753]" />
                    <span>/request-gen-report</span>
                  </>
                )}
              </button>
            </div>

            {/* Diagnostics history index */}
            <div className="flex-1 rounded-2xl border border-[rgba(11,9,7,0.12)] bg-[#fffcf6] p-4 shadow-sm space-y-3 overflow-auto">
              <div>
                <span className="font-mono text-[9px] font-bold text-[#2677ff] uppercase tracking-wider">
                  /registry-history
                </span>
                <h3 className="text-sm font-bold text-[#3c3a39] mt-0.5">Daily Version Registry</h3>
              </div>

              <div className="space-y-2.5">
                {reportsList.map((rep, idx) => (
                  <div
                    key={rep.version}
                    className="rounded-xl border border-[rgba(11,9,7,0.06)] bg-[#fefcf5] p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#3c3a39]">{rep.version}</span>
                      <span className="font-mono text-[9px] text-[rgba(11,9,7,0.4)]">{rep.date}</span>
                    </div>
                    <div className="flex justify-between font-mono text-[9px] text-[rgba(11,9,7,0.5)]">
                      <span>Avg Score: {rep.averageScore}</span>
                      <span>At Risk: {rep.atRiskCount}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        )}
      </section>
    </main>
  );
}

function ReportStat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[rgba(11,9,7,0.06)] bg-[#fffcf6] p-2.5 text-center shadow-xs">
      <span className="block font-mono text-[8px] uppercase tracking-wider text-[rgba(11,9,7,0.4)]">
        {label}
      </span>
      <span className={`block text-sm font-bold mt-1 ${highlight ? "text-[#ff272d]" : "text-[#3c3a39]"}`}>
        {value}
      </span>
    </div>
  );
}
