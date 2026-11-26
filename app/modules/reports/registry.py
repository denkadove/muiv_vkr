"""Реестр доступных отчётов."""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ReportDefinition:
    """Описание отчёта для реестра."""

    key: str
    title: str
    description: str
    generator: Callable[[dict], str]


REPORTS: list[ReportDefinition] = []


def register_report(report: ReportDefinition) -> None:
    """Регистрирует отчёт в реестре."""
    REPORTS.append(report)