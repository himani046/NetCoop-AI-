"""Advisory LangChain structured output, disabled unless configured."""
import os
from pydantic import BaseModel, ConfigDict, Field

class SecondOpinion(BaseModel):
    model_config=ConfigDict(extra="forbid")
    suggested_cause: str|None = None
    explanation: str
    requires_more_data: bool
    alternative_causes: list[str] = Field(default_factory=list)

def structured_second_opinion(telemetry:dict, findings:list[dict])->tuple[SecondOpinion|None,str|None]:
    model=os.getenv("NETCOOP_LLM_MODEL","").strip()
    if not model:
        return None,"Optional LLM disabled (NETCOOP_LLM_MODEL not set)"
    try:
        from langchain.chat_models import init_chat_model
        llm=init_chat_model(model).with_structured_output(SecondOpinion)
        allowed={k:v for k,v in telemetry.items() if isinstance(v,(int,float,str))}
        result=llm.invoke([
            ("system","Offer an advisory network fault diagnosis. Use only supplied telemetry, never invent metrics."),
            ("human",f"Telemetry: {allowed!r}\nAgent findings: {findings!r}")
        ])
        return SecondOpinion.model_validate(result),None
    except Exception as exc:
        return None,f"Optional LLM error: {type(exc).__name__}: {exc}"
