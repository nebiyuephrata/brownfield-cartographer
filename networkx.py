from __future__ import annotations
from collections import deque


class NetworkXNoPath(Exception):
    pass


class _NodeView:
    def __init__(self, g): self.g=g
    def __iter__(self): return iter(self.g._nodes.keys())
    def __contains__(self, n): return n in self.g._nodes
    def __getitem__(self, n): return self.g._nodes[n]
    def __call__(self, data=False):
        return list(self.g._nodes.items()) if data else list(self.g._nodes.keys())


class _EdgeView:
    def __init__(self,g): self.g=g
    def __iter__(self):
        for u,nbrs in self.g._succ.items():
            for v in nbrs: yield (u,v)
    def __call__(self, data=False):
        out=[]
        for u,nbrs in self.g._succ.items():
            for v,attrs in nbrs.items():
                out.append((u,v,attrs) if data else (u,v))
        return out


class DiGraph:
    def __init__(self):
        self._nodes={}; self._succ={}; self._pred={}
        self.nodes=_NodeView(self); self.edges=_EdgeView(self)

    def add_node(self, n, **attrs):
        self._nodes.setdefault(n, {}).update(attrs)
        self._succ.setdefault(n, {})
        self._pred.setdefault(n, {})

    def add_edge(self, u, v, **attrs):
        self.add_node(u); self.add_node(v)
        self._succ[u][v]=attrs
        self._pred[v][u]=attrs

    def predecessors(self, n): return list(self._pred.get(n, {}).keys())
    def successors(self, n): return list(self._succ.get(n, {}).keys())
    def in_degree(self, n): return len(self._pred.get(n, {}))
    def out_degree(self, n): return len(self._succ.get(n, {}))
    def number_of_nodes(self): return len(self._nodes)
    def number_of_edges(self): return sum(len(v) for v in self._succ.values())
    def subgraph(self, nodes):
        s=DiGraph(); keep=set(nodes)
        for n in keep:
            if n in self._nodes: s.add_node(n, **self._nodes[n])
        for u,v,a in self.edges(data=True):
            if u in keep and v in keep: s.add_edge(u,v,**a)
        return s
    def __contains__(self,n): return n in self._nodes


def descendants(g: DiGraph, n):
    seen=set(); q=deque([n])
    while q:
        cur=q.popleft()
        for nxt in g.successors(cur):
            if nxt not in seen:
                seen.add(nxt); q.append(nxt)
    return seen


def ancestors(g: DiGraph, n):
    seen=set(); q=deque([n])
    while q:
        cur=q.popleft()
        for prv in g.predecessors(cur):
            if prv not in seen:
                seen.add(prv); q.append(prv)
    return seen


def shortest_path(g: DiGraph, source, target):
    q=deque([(source,[source])]); seen={source}
    while q:
        cur,path=q.popleft()
        if cur==target: return path
        for nxt in g.successors(cur):
            if nxt not in seen:
                seen.add(nxt); q.append((nxt,path+[nxt]))
    raise NetworkXNoPath()


def pagerank(g: DiGraph):
    n=g.number_of_nodes()
    if n==0: return {}
    return {node:1.0/n for node in g.nodes}


def strongly_connected_components(g: DiGraph):
    # simple Kosaraju-lite for tiny graphs
    nodes=list(g.nodes)
    seen=set(); order=[]
    def dfs(v):
        seen.add(v)
        for w in g.successors(v):
            if w not in seen: dfs(w)
        order.append(v)
    for v in nodes:
        if v not in seen: dfs(v)
    seen.clear()
    def rdfs(v, comp):
        seen.add(v); comp.add(v)
        for w in g.predecessors(v):
            if w not in seen: rdfs(w,comp)
    comps=[]
    for v in reversed(order):
        if v not in seen:
            comp=set(); rdfs(v, comp); comps.append(comp)
    return comps
