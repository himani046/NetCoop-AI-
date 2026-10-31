"""Hierarchy-based blast radius and common upstream detection."""
def analyze_topology(telemetry: dict) -> dict:
    data=telemetry.get("topology") or {}
    nodes=data.get("nodes",[]) if isinstance(data,dict) else []
    if not isinstance(nodes,list):
        return {"scope":"unknown","affected":[],"common_ancestor":None,"warnings":["topology.nodes must be a list"]}
    mapping={}; warnings=[]
    for item in nodes:
        if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not item["id"]:
            warnings.append("Invalid topology node ignored")
        elif item["id"] in mapping:
            warnings.append("Duplicate node: "+item["id"])
        else:
            mapping[item["id"]]=item
    raw=telemetry.get("affected_device_ids") or []
    if not isinstance(raw,list):
        raw=[]; warnings.append("affected_device_ids must be a list")
    affected=[x for x in raw if isinstance(x,str) and x in mapping]
    for x in raw:
        if x not in mapping:
            warnings.append("Unknown affected device: "+str(x))
    paths=[]
    for x in affected:
        path=[]; seen=set()
        while x in mapping:
            if x in seen:
                warnings.append("Topology cycle detected: "+x)
                break
            seen.add(x); path.append(x); x=mapping[x].get("parent_id")
        paths.append(path)
    common=set(paths[0]).intersection(*(set(p) for p in paths[1:])) if paths else set()
    ancestor=next((x for x in paths[0] if x in common),None) if paths else None
    sites={mapping[x].get("site") for x in affected}
    scope="unknown"
    if len(affected)==1: scope="single_device"
    elif len(affected)>1: scope="local_segment" if len(sites)==1 else "multi_site"
    if ancestor and mapping[ancestor].get("role") in {"core","core_router","gateway"} and len(sites)>1:
        scope="campus_core"
    return {"scope":scope,"affected":affected,"common_ancestor":ancestor,"paths":paths,"warnings":warnings}
