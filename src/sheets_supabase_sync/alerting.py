from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from .operational_events import OperationalEvent, Severity, log_operational_event, sanitize_text


class AlertSink(Protocol):
    def send(self, event: OperationalEvent) -> None: ...


@dataclass
class InMemoryAlertSink:
    events: list[OperationalEvent] = field(default_factory=list)

    def send(self, event: OperationalEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class AlertPolicy:
    alert_warnings: bool = False

    def eligible(self, event: OperationalEvent) -> bool:
        return event.severity in {Severity.ERROR, Severity.CRITICAL} or (self.alert_warnings and event.severity is Severity.WARNING)


@dataclass
class AlertDeduplicator:
    cooldown: timedelta
    sent: dict[tuple[str, str, str | None], datetime] = field(default_factory=dict)

    def allow(self, event: OperationalEvent) -> bool:
        key = (event.component, event.error_category or event.outcome, event.source_ref)
        previous = self.sent.get(key)
        if previous and event.timestamp - previous < self.cooldown:
            return False
        self.sent[key] = event.timestamp
        return True


class OperationalReporter:
    def __init__(self, logger: logging.Logger, sink: AlertSink | None = None, policy: AlertPolicy = AlertPolicy(), deduplicator: AlertDeduplicator | None = None) -> None:
        self._logger, self._sink, self._policy = logger, sink, policy
        self._deduplicator = deduplicator or AlertDeduplicator(timedelta(minutes=15))

    def emit(self, event: OperationalEvent) -> None:
        log_operational_event(self._logger, event)
        if self._sink and self._policy.eligible(event) and self._deduplicator.allow(event):
            try:
                self._sink.send(event)
            except Exception:
                self._logger.error('{"event":"alert_transport_unavailable"}')


class SmtpAlertSink:
    def __init__(self, host: str | None, sender: str | None, recipient: str | None, smtp_factory: Callable[[str], smtplib.SMTP] = smtplib.SMTP) -> None:
        self._host, self._sender, self._recipient, self._smtp_factory = host, sender, recipient, smtp_factory

    def send(self, event: OperationalEvent) -> None:
        if not all((self._host, self._sender, self._recipient)):
            raise RuntimeError("alert_transport_disabled")
        message = EmailMessage()
        message["Subject"] = f"[{event.severity.value}] {sanitize_text(event.component)} {sanitize_text(event.error_category or event.outcome)}"
        message["From"], message["To"] = self._sender, self._recipient
        message.set_content("\n".join((f"severity={event.severity.value}", f"component={sanitize_text(event.component)}", f"source_ref={sanitize_text(event.source_ref or '')}", f"category={sanitize_text(event.error_category or event.outcome)}", f"attempt={event.attempt or 0}", "consult_logs_and_runbook=true")))
        with self._smtp_factory(self._host) as smtp:
            smtp.send_message(message)
