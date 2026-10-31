"""SQLite ORM schema. Telemetry and agent payloads retained as JSON snapshots."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utc_now():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    site: Mapped[str | None] = mapped_column(String(200))
    parent_id: Mapped[str | None] = mapped_column(String(200))
    incidents: Mapped[list["Incident"]] = relationship(back_populates="device")

class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(200), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(40))
    suspected_root_cause: Mapped[str] = mapped_column(String(250))
    confidence: Mapped[float] = mapped_column(Float)
    raw_telemetry_json: Mapped[str] = mapped_column(Text)
    normalized_telemetry_json: Mapped[str] = mapped_column(Text)
    report_json: Mapped[str] = mapped_column(Text)
    markdown_report: Mapped[str] = mapped_column(Text)
    warnings_json: Mapped[str] = mapped_column(Text)
    device: Mapped["Device"] = relationship(back_populates="incidents")
    messages: Mapped[list["AgentMessage"]] = relationship(back_populates="incident", cascade="all, delete-orphan")

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_pk: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    message_order: Mapped[int] = mapped_column(Integer)
    sender: Mapped[str] = mapped_column(String(150))
    recipient: Mapped[str] = mapped_column(String(150))
    payload_json: Mapped[str] = mapped_column(Text)
    incident: Mapped["Incident"] = relationship(back_populates="messages")
