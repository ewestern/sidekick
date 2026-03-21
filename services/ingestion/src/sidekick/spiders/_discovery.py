"""Discover spider classes registered in the spiders package."""

from __future__ import annotations

import importlib
import logging
import pkgutil

import sidekick.spiders as _spiders_pkg
from sidekick.spiders._base import SidekickSpider

logger = logging.getLogger(__name__)


def discover_spiders() -> dict[str, type[SidekickSpider]]:
    """Scan the spiders package and return ``{source_id: spider_class}``.

    Skips modules whose names start with ``_`` (harness infrastructure).
    Raises ``ValueError`` if a spider class fails ``SpiderMeta`` validation or
    if the same ``source_id`` appears in more than one module.
    """
    result: dict[str, type[SidekickSpider]] = {}

    for module_info in pkgutil.iter_modules(_spiders_pkg.__path__):
        if module_info.name.startswith("_"):
            continue

        mod_name = f"{_spiders_pkg.__name__}.{module_info.name}"
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:
            logger.warning("Could not import spider module %s: %s", mod_name, exc)
            continue

        for attr_name in dir(mod):
            obj = getattr(mod, attr_name)
            if not (
                isinstance(obj, type)
                and issubclass(obj, SidekickSpider)
                and obj is not SidekickSpider
                and obj.__module__ == mod.__name__
            ):
                continue

            try:
                meta = obj.get_meta()
            except Exception as exc:
                raise ValueError(
                    f"Spider {obj.__name__} in {module_info.name} failed validation: {exc}"
                ) from exc

            if meta.source_id in result:
                existing = result[meta.source_id]
                raise ValueError(
                    f"Duplicate source_id {meta.source_id!r} defined in "
                    f"{existing.__module__} and {mod.__name__}"
                )

            result[meta.source_id] = obj
            logger.debug("Discovered spider %s -> %s", meta.source_id, obj.__name__)

    return result
