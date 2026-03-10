import { useEffect, useRef, useState, useCallback } from "react";
import { Box, Typography, Skeleton } from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";
import { useQuery } from "@tanstack/react-query";
import { fetchOutletNetwork } from "../api";
import type { NetworkNode, NetworkEdge } from "../api";

interface SimNode extends NetworkNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function useForceSimulation(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  width: number,
  height: number
) {
  const [simNodes, setSimNodes] = useState<SimNode[]>([]);
  const frameRef = useRef<number>(0);
  const iterRef = useRef(0);

  useEffect(() => {
    if (!nodes.length || !width || !height) return;

    // Initialize positions in a circle
    const initialized: SimNode[] = nodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const r = Math.min(width, height) * 0.3;
      return {
        ...n,
        x: width / 2 + r * Math.cos(angle),
        y: height / 2 + r * Math.sin(angle),
        vx: 0,
        vy: 0,
      };
    });

    const nodeMap = new Map<string, SimNode>();
    initialized.forEach((n) => nodeMap.set(n.id, n));
    iterRef.current = 0;

    const tick = () => {
      iterRef.current++;
      if (iterRef.current > 300) return; // stop after convergence

      const alpha = Math.max(0.001, 1 - iterRef.current / 300);
      const nodes = [...nodeMap.values()];

      // Repulsion (all pairs)
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = (800 * alpha) / (dist * dist);
          dx = (dx / dist) * force;
          dy = (dy / dist) * force;
          a.vx -= dx;
          a.vy -= dy;
          b.vx += dx;
          b.vy += dy;
        }
      }

      // Attraction (edges)
      for (const edge of edges) {
        const a = nodeMap.get(edge.source);
        const b = nodeMap.get(edge.target);
        if (!a || !b) continue;
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = (dist - 80) * 0.02 * alpha * Math.min(edge.weight, 5);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        a.vx += dx;
        a.vy += dy;
        b.vx -= dx;
        b.vy -= dy;
      }

      // Center gravity
      for (const n of nodes) {
        n.vx += (width / 2 - n.x) * 0.005 * alpha;
        n.vy += (height / 2 - n.y) * 0.005 * alpha;
      }

      // Apply velocity with damping
      for (const n of nodes) {
        n.vx *= 0.6;
        n.vy *= 0.6;
        n.x += n.vx;
        n.y += n.vy;
        // Keep within bounds
        n.x = Math.max(30, Math.min(width - 30, n.x));
        n.y = Math.max(30, Math.min(height - 30, n.y));
      }

      setSimNodes([...nodes]);
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [nodes, edges, width, height]);

  return simNodes;
}

export const OutletNetworkGraph = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const { data: graph, isLoading } = useQuery({
    queryKey: ["outlet-network"],
    queryFn: fetchOutletNetwork,
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });

  const measureDims = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setDims({ width: rect.width, height: rect.height });
    }
  }, []);

  useEffect(() => {
    measureDims();
    window.addEventListener("resize", measureDims);
    return () => window.removeEventListener("resize", measureDims);
  }, [measureDims]);

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const simNodes = useForceSimulation(nodes, edges, dims.width, dims.height);

  const nodeMap = new Map<string, SimNode>();
  simNodes.forEach((n) => nodeMap.set(n.id, n));

  const getNodeColor = (n: SimNode) => {
    if (n.color) return n.color;
    if (n.type === "narrative") return "#f59e0b";
    return "#3b82f6";
  };

  const getNodeRadius = (n: SimNode) => {
    return Math.max(6, Math.min(18, 4 + n.size * 3));
  };

  const isHighlighted = (nodeId: string) => {
    if (!hoveredNode) return true;
    if (nodeId === hoveredNode) return true;
    return edges.some(
      (e) =>
        (e.source === hoveredNode && e.target === nodeId) ||
        (e.target === hoveredNode && e.source === nodeId)
    );
  };

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "rgba(12, 20, 56, 0.6)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(148,163,184,0.1)",
        borderRadius: 3,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1.5,
          borderBottom: "1px solid rgba(148,163,184,0.08)",
          flexShrink: 0,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <HubIcon sx={{ fontSize: 16, color: "#8b5cf6" }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Outlet Network
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#3b82f6" }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6rem" }}>Outlet</Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#f59e0b" }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.6rem" }}>Narrative</Typography>
          </Box>
        </Box>
      </Box>

      <Box ref={containerRef} sx={{ flexGrow: 1, minHeight: 0, position: "relative" }}>
        {isLoading ? (
          <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 0, backgroundColor: "rgba(255,255,255,0.04)" }} />
        ) : !nodes.length ? (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Typography variant="body2" color="text.secondary">
              No network data yet — complete analyses to build the graph
            </Typography>
          </Box>
        ) : (
          <svg width={dims.width} height={dims.height} style={{ display: "block" }}>
            {/* Edges */}
            {edges.map((e, i) => {
              const a = nodeMap.get(e.source);
              const b = nodeMap.get(e.target);
              if (!a || !b) return null;
              const highlighted = isHighlighted(e.source) && isHighlighted(e.target);
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={highlighted ? "rgba(148,163,184,0.25)" : "rgba(148,163,184,0.05)"}
                  strokeWidth={Math.max(0.5, Math.min(e.weight, 4))}
                />
              );
            })}

            {/* Nodes */}
            {simNodes.map((n) => {
              const r = getNodeRadius(n);
              const color = getNodeColor(n);
              const highlighted = isHighlighted(n.id);
              const isHovered = hoveredNode === n.id;
              return (
                <g
                  key={n.id}
                  onMouseEnter={() => setHoveredNode(n.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  style={{ cursor: "pointer" }}
                >
                  {/* Glow */}
                  {isHovered && (
                    <circle cx={n.x} cy={n.y} r={r + 6} fill={color} opacity={0.15} />
                  )}
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={r}
                    fill={color}
                    opacity={highlighted ? 0.9 : 0.15}
                    stroke={isHovered ? "#fff" : "none"}
                    strokeWidth={1.5}
                  />
                  {/* Label */}
                  {(r >= 8 || isHovered) && (
                    <text
                      x={n.x}
                      y={n.y + r + 12}
                      textAnchor="middle"
                      fill={highlighted ? "#94a3b8" : "rgba(148,163,184,0.2)"}
                      fontSize={n.type === "narrative" ? 8 : 9}
                      fontWeight={isHovered ? 700 : 400}
                      fontFamily="inherit"
                    >
                      {n.label.length > 18 ? n.label.slice(0, 17) + "…" : n.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        )}
      </Box>
    </Box>
  );
};
