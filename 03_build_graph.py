"""
Step 4 — 지식 그래프 (안내문 옵션 B: networkx). Neo4j 금지 대응.
----------------------------------------------------------------
extract/records.jsonl → 속성 그래프.
노드: Source, Article, Person/Org/Place/Concept, Event, CausalAssertion, Mention
엣지: DERIVED_FROM, SUPPORTED_BY(quote), ABOUT, CAUSE, EFFECT, EVIDENCE
산출: graph/kg.graphml  (제출용), graph/nodes.csv, graph/edges.csv
"""
import json, csv, os
import networkx as nx

G = nx.MultiDiGraph()

def add(nid, **attr):
    if nid not in G: G.add_node(nid, **attr)

def main():
    recs=[json.loads(l) for l in open("extract/records.jsonl",encoding="utf-8")]
    add("SRC:EveningStar", ntype="Source", label="Evening Star")
    for rec in recs:
        aid=rec["article_id"]
        add(f"ART:{aid}", ntype="Article", date=rec["date"], period=rec["period"])
        G.add_edge(f"ART:{aid}","SRC:EveningStar", etype="DERIVED_FROM")

        for e in rec.get("entities",[]):
            nid=f"{e['type']}:{e['label']}"
            add(nid, ntype=e["type"], label=e["label"])
            mid=f"MENTION:{aid}:{e['label']}"
            add(mid, ntype="Mention", label=e.get("quote",""))
            G.add_edge(nid,mid, etype="SUPPORTED_BY")
            G.add_edge(mid,f"ART:{aid}", etype="DERIVED_FROM")
            G.add_edge(nid,f"ART:{aid}", etype="ABOUT", quote=e.get("quote",""))

        for j,ev in enumerate(rec.get("events",[])):
            eid=f"EVENT:{aid}:{j}"
            add(eid, ntype="Event", label=ev["label"], date_hint=ev.get("date_hint",""))
            G.add_edge(eid,f"ART:{aid}", etype="ABOUT", quote=ev.get("quote",""))
            mid=f"MENTION:{aid}:event{j}"
            add(mid, ntype="Mention", label=ev.get("quote",""))
            G.add_edge(eid,mid, etype="SUPPORTED_BY")
            G.add_edge(mid,f"ART:{aid}", etype="DERIVED_FROM")

        for i,c in enumerate(rec.get("causal_assertions",[])):
            ca=f"CA:{aid}:{i}"
            add(ca, ntype="CausalAssertion", relation=c["relation"],
                sign=c.get("sign"), confidence=c.get("confidence"),
                frame=c.get("frame"), period=rec["period"])
            add(f"Concept:{c['cause']}", ntype="Concept", label=c["cause"])
            add(f"Concept:{c['effect']}", ntype="Concept", label=c["effect"])
            G.add_edge(ca,f"Concept:{c['cause']}", etype="CAUSE")
            G.add_edge(ca,f"Concept:{c['effect']}", etype="EFFECT")
            mid=f"MENTION:{aid}:ca{i}"
            add(mid, ntype="Mention", label=c["quote"])
            G.add_edge(ca,mid, etype="EVIDENCE")
            G.add_edge(mid,f"ART:{aid}", etype="DERIVED_FROM")

    os.makedirs("graph",exist_ok=True)
    nx.write_graphml(G,"graph/kg.graphml")
    with open("graph/nodes.csv","w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["id","ntype","label"])
        for n,d in G.nodes(data=True): w.writerow([n,d.get("ntype"),d.get("label","")])
    with open("graph/edges.csv","w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["src","dst","etype","quote"])
        for u,v,d in G.edges(data=True): w.writerow([u,v,d.get("etype"),d.get("quote","")])
    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()} → graph/")

if __name__=="__main__":
    main()
