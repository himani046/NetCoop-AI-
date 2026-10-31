"""Explicit demo-only device placement; no claim of real campus topology."""
from sqlalchemy import String, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column
from src.database.models import Base

class DemoAssignment(Base):
    __tablename__="demo_campus_assignments"
    device_id:Mapped[str]=mapped_column(String(200),primary_key=True)
    region_id:Mapped[str]=mapped_column(String(50),nullable=False)

REGIONS=[
 {"id":"main","name":"Main Building","latitude":20.14827,"longitude":85.67108},
 {"id":"lalitgiri","name":"Lalitgiri Lecture Hall","latitude":20.14684,"longitude":85.67411},
 {"id":"pushpagiri","name":"Pushpagiri Lecture Hall","latitude":20.14640,"longitude":85.67558},
 {"id":"labs","name":"Lab Complex","latitude":20.14819,"longitude":85.67761},
 {"id":"campus","name":"Campus Reference","latitude":20.14797,"longitude":85.67007},
]
def campus_snapshot(session, latest):
    placements={row.device_id:row.region_id for row in session.scalars(select(DemoAssignment)).all()}
    by_region={r["id"]:[] for r in REGIONS}
    for device in latest:
        rid=placements.get(device["device_id"])
        if rid in by_region:by_region[rid].append(device)
    enriched=[]
    for region in REGIONS:
        devices=by_region[region["id"]]
        state=("fault" if any(d["status"]=="diagnosed" for d in devices) else
               "limited" if any(d["status"]=="inconclusive" for d in devices) else
               "healthy" if devices else "unmonitored")
        enriched.append({**region,"status":state,"devices":devices})
    return {"live":False,"mode":"MANUAL DEMO ASSIGNMENTS","regions":enriched,
            "device_assignments":[{"device_id":k,"region_id":v} for k,v in sorted(placements.items())]}

def historical_campus_frames(session, events):
    """Use the same demo assignments for every historical frame; unobserved devices are absent."""
    placements={row.device_id:row.region_id for row in session.scalars(select(DemoAssignment)).all()}
    times=sorted({event["observed_at"] for event in events if event["observed_at"]})
    ordered=sorted((e for e in events if e["observed_at"]),key=lambda e:(e["observed_at"],e["record_id"]))
    current={}
    frames=[]
    offset=0
    for stamp in times:
        while offset<len(ordered) and ordered[offset]["observed_at"]<=stamp:
            e=ordered[offset]
            current[e["device_id"]]=e
            offset+=1
        grouped={r["id"]:[] for r in REGIONS}
        for device_id,event in current.items():
            region=placements.get(device_id)
            if region in grouped:
                grouped[region].append({"device_id":device_id,"status":event["status"],
                    "root_cause":event["root_cause"],"record_id":event["record_id"],
                    "observed_at":event["observed_at"]})
        regions=[]
        for region in REGIONS:
            devices=sorted(grouped[region["id"]],key=lambda d:d["device_id"])
            state=("fault" if any(d["status"]=="diagnosed" for d in devices)
                else "limited" if any(d["status"]!="healthy" for d in devices)
                else "healthy" if devices else "unmonitored")
            regions.append({**region,"status":state,"devices":devices})
        frames.append({"observed_at":stamp,"regions":regions,
            "device_count":len(current),"mapped_device_count":sum(len(v) for v in grouped.values())})
    return {"frames":frames,"live":False,"mode":"HISTORICAL SIMULATED CAMPUS",
        "assignment_policy":"Current manual demo placements are applied retroactively; no location history is recorded."}
