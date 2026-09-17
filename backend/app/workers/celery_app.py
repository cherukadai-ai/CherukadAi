"""Celery application factory.

Task modules are registered per-module as they're implemented; this phase only
wires the broker/backend and confirms the worker process boots.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cherukadai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("app.modules.interior_design.worker",),
)
