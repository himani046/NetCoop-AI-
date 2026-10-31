"""SQLite persistence regression tests."""
from src.database.models import AgentMessage, Incident, Device
from src.database.session import session_factory
from src.database.repository import save_incident, list_incidents, get_incident
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
from main import run_batch

def test_save_reload_incident_and_messages(tmp_path):
    path=tmp_path/"incidents.db"
    raw=scenarios()["link_congestion"]
    state=diagnose(raw,"INC-DB-TEST")
    with session_factory(path)() as session:
        pk=save_incident(session,raw,state)
    with session_factory(path)() as session:
        found=get_incident(session,pk)
        assert found["report"]["suspected_root_cause"]=="link_congestion"
        assert found["device_id"]==raw["device_id"]
        assert len(found["messages"])==len(state["messages"])
        assert session.query(Device).count()==1
        assert session.query(Incident).count()==1
        assert session.query(AgentMessage).count()==len(state["messages"])

def test_repeat_runs_distinct_history(tmp_path):
    path=tmp_path/"incidents.db"
    raw=scenarios()["normal_operation"]
    with session_factory(path)() as session:
        save_incident(session,raw,diagnose(raw,"INC-SAME"))
        save_incident(session,raw,diagnose(raw,"INC-SAME"))
        assert len(list_incidents(session))==2
        assert list_incidents(session)[0]["id"] != list_incidents(session)[1]["id"]

def test_batch_persists_across_sessions(tmp_path):
    path=tmp_path/"incident_store.sqlite"
    fixture=__import__("pathlib").Path(__file__).resolve().parents[1]/"data"/"colab_batch.json"
    result=run_batch(fixture,path)
    assert result["total"]==3
    assert result["errors"]==0
    with session_factory(path)() as session:
        assert len(list_incidents(session))==3
