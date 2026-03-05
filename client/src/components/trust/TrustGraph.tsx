import { useEffect, useRef, memo } from "react";
import { cn } from "@/lib/utils";

export interface TrustNode {
  id: string;
  label: string;
  trust_score: number;
  group?: string;
}

export interface TrustEdge {
  source: string;
  target: string;
  weight: number;
}

interface TrustGraphProps {
  nodes: TrustNode[];
  edges: TrustEdge[];
  width?: number;
  height?: number;
  className?: string;
  onNodeClick?: (node: TrustNode) => void;
}

function getSignalColor(score: number): string {
  const root = getComputedStyle(document.documentElement);
  if (score >= 70) return `hsl(${root.getPropertyValue("--signal-green").trim()})`;
  if (score >= 30) return `hsl(${root.getPropertyValue("--signal-blue").trim()})`;
  if (score >= 0) return `hsl(${root.getPropertyValue("--signal-amber").trim()})`;
  return `hsl(${root.getPropertyValue("--signal-red").trim()})`;
}

export const TrustGraph = memo(function TrustGraph({
  nodes,
  edges,
  width = 600,
  height = 400,
  className,
  onNodeClick,
}: TrustGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);
  const simulationRef = useRef<any>(null);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }
      const svg = svgRef.current;
      if (svg) {
        while (svg.firstChild) svg.removeChild(svg.firstChild);
      }
    };
  }, []);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || nodes.length === 0) return;

    if (simulationRef.current) {
      simulationRef.current.stop();
      simulationRef.current = null;
    }
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    let cancelled = false;

    (async () => {
      const d3 = await import("d3");
      if (cancelled || !mountedRef.current) return;

      const svgSelection = d3.select(svg)
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

      svgSelection.on(".zoom", null);

      const g = svgSelection.append("g");

      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.3, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform.toString());
        });

      svgSelection.call(zoom);

      const nodeMap = new Map(nodes.map((n) => [n.id, n]));
      const simLinks = edges
        .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
        .map((e) => ({ ...e }));
      const simNodes = nodes.map((n) => ({ ...n, x: 0, y: 0 }));

      const simulation = d3.forceSimulation(simNodes as any)
        .force("link", d3.forceLink(simLinks as any).id((d: any) => d.id).distance(80))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius((d: any) => Math.max(10, d.trust_score / 5) + 8));

      simulationRef.current = simulation;

      g.append("g")
        .selectAll("line")
        .data(simLinks)
        .join("line")
        .attr("stroke", "rgba(255,255,255,0.08)")
        .attr("stroke-width", (d: any) => Math.max(0.5, d.weight * 2));

      const link = g.selectAll("line");

      const node = g.append("g")
        .selectAll("g")
        .data(simNodes)
        .join("g")
        .attr("cursor", "pointer")
        .on("click", (_event: any, d: any) => {
          const original = nodeMap.get(d.id);
          if (original && onNodeClick) onNodeClick(original);
        });

      node.append("circle")
        .attr("r", (d: any) => Math.max(6, Math.abs(d.trust_score) / 5))
        .attr("fill", (d: any) => getSignalColor(d.trust_score))
        .attr("opacity", 0.8)
        .attr("stroke", "rgba(255,255,255,0.1)")
        .attr("stroke-width", 1);

      node.append("text")
        .text((d: any) => d.label.slice(0, 8))
        .attr("dy", (d: any) => Math.max(6, Math.abs(d.trust_score) / 5) + 12)
        .attr("text-anchor", "middle")
        .attr("fill", "rgba(255,255,255,0.5)")
        .attr("font-size", "9px")
        .attr("font-family", "var(--font-mono)");

      simulation.on("tick", () => {
        if (!mountedRef.current) {
          simulation.stop();
          return;
        }
        link
          .attr("x1", (d: any) => d.source.x)
          .attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x)
          .attr("y2", (d: any) => d.target.y);
        node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
      });
    })();

    return () => {
      cancelled = true;
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }
      const svgEl = svgRef.current;
      if (svgEl) {
        const d3Sel = (window as any).__d3_select_cache;
        if (!d3Sel) {
          while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);
        }
      }
    };
  }, [nodes, edges, width, height, onNodeClick]);

  return (
    <div ref={containerRef} className={cn("w-full h-full", className)} data-testid="trust-graph-container">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
});
