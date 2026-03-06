import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Download, FileText, FileSpreadsheet, FileJson } from "lucide-react";

type ExportFormat = "pdf" | "csv" | "json";

interface ExportMenuProps {
  onExport: (format: ExportFormat) => void;
  label?: string;
  "data-testid"?: string;
}

export function ExportMenu({ onExport, label = "Export", ...props }: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative" data-testid={props["data-testid"] || "export-menu"}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-colors"
        data-testid="btn-export-toggle"
      >
        <Download className="w-3.5 h-3.5" />
        <span>{label}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 glass-panel-elevated rounded-lg border border-white/[0.06] py-1 w-36 animate-in fade-in-0 zoom-in-95 duration-100">
          <button
            onClick={() => { onExport("pdf"); setOpen(false); }}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-white/[0.04] transition-colors"
            data-testid="btn-export-pdf"
          >
            <FileText className="w-3.5 h-3.5 text-signal-red" />
            PDF Report
          </button>
          <button
            onClick={() => { onExport("csv"); setOpen(false); }}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-white/[0.04] transition-colors"
            data-testid="btn-export-csv"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-signal-green" />
            CSV Data
          </button>
          <button
            onClick={() => { onExport("json"); setOpen(false); }}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-white/[0.04] transition-colors"
            data-testid="btn-export-json"
          >
            <FileJson className="w-3.5 h-3.5 text-signal-blue" />
            JSON Export
          </button>
        </div>
      )}
    </div>
  );
}
