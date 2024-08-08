import logging

from fastapi import HTTPException

from trading_api.core.container import Container

logger = logging.getLogger(__name__)


def handle_health_request(container: Container):
    healthy = True
    for service in container.keys():
        if not hasattr(service, "is_healthy"):
            continue
        try:
            if not container[service].is_healthy():
                logger.error(f"[HEALTH] {service.__name__} health check FAILED")
                healthy = False
        except Exception as e:
            logger.error(f"[HEALTH] {service.__name__} health check FAILED. {e=}")
            healthy = False

    if not healthy:
        raise HTTPException(status_code=500, detail="Service is not healthy.")
