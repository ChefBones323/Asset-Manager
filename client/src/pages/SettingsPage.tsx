import { ExportMenu } from "@/components/common/ExportMenu";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardBody } from "@/components/common/Card";
import { printConfigurationHistory } from "@/services/export/printService";
import { Settings, Download, Clock } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="h-full p-4 overflow-y-auto" data-testid="settings-page">
      <div className="max-w-2xl mx-auto space-y-4">
        <GlassCard variant="elevated">
          <GlassCardHeader>
            <GlassCardTitle>
              <Settings className="w-3.5 h-3.5 inline mr-1.5 text-muted-foreground" />
              System Configuration
            </GlassCardTitle>
          </GlassCardHeader>
          <GlassCardBody className="space-y-4">
            <p className="text-xs text-muted-foreground">
              System configuration management and policy administration.
            </p>

            <div className="glass-inset rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-signal-amber" />
                  <span className="text-xs font-medium text-foreground">Configuration History</span>
                </div>
                <ExportMenu
                  onExport={(f) => printConfigurationHistory(f)}
                  label="Export History"
                  data-testid="export-config-history"
                />
              </div>
              <p className="text-[10px] text-muted-foreground">
                Export a complete record of all configuration and policy changes, including feed policy activations, config updates, and system parameter modifications.
              </p>
            </div>

            <div className="glass-inset rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Download className="w-3.5 h-3.5 text-signal-blue" />
                <span className="text-xs font-medium text-foreground">Data Management</span>
              </div>
              <p className="text-[10px] text-muted-foreground">
                Export reports are available on each page (Governance, Feed, Trust, Events) via the Export button. Use the Command Palette (Cmd+K) and search "export" for quick access.
              </p>
            </div>
          </GlassCardBody>
        </GlassCard>
      </div>
    </div>
  );
}
