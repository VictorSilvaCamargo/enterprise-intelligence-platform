"""Architectural extension registry for planned platform domain modules."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Metadata describing a planned modular monolith capability."""

    key: str
    display_name: str
    target_stage: int
    api_prefix: str
    summary: str


PLANNED_MODULES: tuple[ModuleDescriptor, ...] = (
    ModuleDescriptor(
        key="data_integration",
        display_name="Data Integration",
        target_stage=2,
        api_prefix="/data-integration",
        summary="Ingestion connectors, schema contracts, and synchronization pipelines.",
    ),
    ModuleDescriptor(
        key="ai_knowledge_hub",
        display_name="AI Knowledge Hub",
        target_stage=4,
        api_prefix="/knowledge-hub",
        summary="Document indexing, embeddings, and RAG retrieval services.",
    ),
    ModuleDescriptor(
        key="ai_agents",
        display_name="AI Agents",
        target_stage=5,
        api_prefix="/agents",
        summary="Multi-agent runtime, tool orchestration, and task execution.",
    ),
    ModuleDescriptor(
        key="business_intelligence",
        display_name="Business Intelligence",
        target_stage=6,
        api_prefix="/intelligence",
        summary="Analytical KPI queries, reporting views, and ML forecasting.",
    ),
    ModuleDescriptor(
        key="workflow_automation",
        display_name="Workflow Automation",
        target_stage=7,
        api_prefix="/workflows",
        summary="Event-driven orchestration, background queues, and scheduled jobs.",
    ),
)


def register_module_router(
    parent_router: APIRouter,
    module_router: APIRouter,
    descriptor: ModuleDescriptor,
) -> None:
    """Attach a future module router under the versioned API boundary."""
    parent_router.include_router(
        module_router,
        prefix=descriptor.api_prefix,
        tags=[descriptor.display_name],
    )
