import { cn } from "@/lib/utils";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "inset";
  glow?: "none" | "blue" | "green" | "amber" | "red" | "purple";
}

export function GlassCard({
  className,
  variant = "default",
  glow = "none",
  children,
  ...props
}: GlassCardProps) {
  const glowStyles: Record<string, string> = {
    none: "",
    blue: "shadow-[0_0_20px_-4px_hsl(var(--signal-blue)/0.15)]",
    green: "shadow-[0_0_20px_-4px_hsl(var(--signal-green)/0.15)]",
    amber: "shadow-[0_0_20px_-4px_hsl(var(--signal-amber)/0.15)]",
    red: "shadow-[0_0_20px_-4px_hsl(var(--signal-red)/0.15)]",
    purple: "shadow-[0_0_20px_-4px_hsl(var(--signal-purple)/0.15)]",
  };

  const variantClass =
    variant === "elevated"
      ? "glass-panel-elevated"
      : variant === "inset"
        ? "glass-inset"
        : "glass-panel";

  return (
    <div
      className={cn(
        variantClass,
        "rounded-lg",
        glowStyles[glow],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function GlassCardHeader({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-between px-4 py-3 border-b border-white/[0.06]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function GlassCardTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("mono-label", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function GlassCardBody({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-4", className)} {...props}>
      {children}
    </div>
  );
}
