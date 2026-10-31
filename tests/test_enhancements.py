import pytest
from src.utils.calibration import fit_bins, calibrated_probability
from src.utils.topology import analyze_topology

def test_bins_and_abstention():
    model=fit_bins([{"score":.82,"correct":True} for _ in range(25)])
    assert calibrated_probability(.82,model) > .9
    assert calibrated_probability(.2,model) is None
    with pytest.raises(ValueError):
        fit_bins([])

def test_common_upstream():
    data={"topology":{"nodes":[
        {"id":"AP1","parent_id":"SW1","site":"A"},
        {"id":"AP2","parent_id":"SW2","site":"B"},
        {"id":"SW1","parent_id":"CORE"},
        {"id":"SW2","parent_id":"CORE"},
        {"id":"CORE","role":"core"}]},
        "affected_device_ids":["AP1","AP2"]}
    r=analyze_topology(data)
    assert r["scope"]=="campus_core"
    assert r["common_ancestor"]=="CORE"
