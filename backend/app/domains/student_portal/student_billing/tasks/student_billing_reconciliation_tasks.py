from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.domains.student_portal.student_billing.constants import (
    BILLING_RECONCILIATION_STALE_ORDER_MINUTES,
    BILLING_RECONCILIATION_SWEEP_LIMIT,
)
from app.domains.student_portal.student_billing.services.billing_reconciliation_service import (
    billing_reconciliation_service,
)

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None


def _get_billing_worker_event_loop() -> asyncio.AbstractEventLoop:
    global _loop

    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)

    return _loop

async def _run_billing_reconciliation_sweep_async() -> dict[str, int]:
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        summary = await billing_reconciliation_service.run_reconciliation_sweep(
            db=db,
            older_than_minutes=BILLING_RECONCILIATION_STALE_ORDER_MINUTES,
            limit=BILLING_RECONCILIATION_SWEEP_LIMIT,
        )
        return summary


@celery_app.task(
    name="app.domains.student_portal.student_billing.tasks.student_billing_reconciliation_tasks.run_billing_reconciliation_sweep",
    bind=True,
)
def run_billing_reconciliation_sweep(self) -> dict[str, int]:
    """
    Periodic billing reconciliation sweep.

    Design rules:
    - task contains no business logic; delegates to reconciliation service
    - each reconciliation candidate is handled within service-level safe boundaries
    - task remains isolated to billing_queue via Celery routing
    - a persistent event loop is reused per billing worker process to avoid
      cross-loop async engine / asyncpg failures
    """
    logger.info("Starting billing reconciliation sweep task.")
    loop = _get_billing_worker_event_loop()
    summary = loop.run_until_complete(_run_billing_reconciliation_sweep_async())
    logger.info("Completed billing reconciliation sweep task with summary=%s", summary)
    return summary