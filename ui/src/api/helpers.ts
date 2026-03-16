import type { GraphPayload } from "./cartography";

export function deriveGraphSummary(graph?: GraphPayload | null) {
  if (!graph) {
    return { nodes: 0, edges: 0 };
  }
  return { nodes: graph.nodes?.length ?? 0, edges: graph.edges?.length ?? 0 };
}

export function selectGraphFocus(graph?: GraphPayload | null, maxNodes = 10): GraphPayload | null {
  if (!graph || !graph.nodes?.length) return null;
  const nodes = [...graph.nodes].slice(0, maxNodes);
  const nodeSet = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => nodeSet.has(edge.source) && nodeSet.has(edge.target));
  return { nodes, edges };
}
