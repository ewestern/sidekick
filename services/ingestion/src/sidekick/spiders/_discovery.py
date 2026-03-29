"""Discover spider classes registered in the spiders package."""

from __future__ import annotations

import importlib.util
import logging
import pathlib
import sys

import sidekick.spiders as _spiders_pkg
from sidekick.spiders._base import SidekickSpider

logger = logging.getLogger(__name__)

_SPIDERS_DIR = pathlib.Path(_spiders_pkg.__file__).parent
_PKG_NAME = _spiders_pkg.__name__


def discover_spiders() -> dict[str, type[SidekickSpider]]:
    """Scan the spiders directory recursively and return ``{source_id: spider_class}``.

    Skips any ``.py`` file whose path contains a segment starting with ``_``
    (harness infrastructure).  Geo subdirectories are plain directories — no
    ``__init__.py`` required.

    Raises ``ValueError`` if a spider class fails ``SpiderMeta`` validation or
    if the same ``source_id`` appears in more than one file.
    """
    result: dict[str, type[SidekickSpider]] = {}

    for path in sorted(_SPIDERS_DIR.rglob("*.py")):
        rel = path.relative_to(_SPIDERS_DIR)
        if any(part.startswith("_") for part in rel.parts):
            continue

        mod_name = f"{_PKG_NAME}." + ".".join(rel.with_suffix("").parts)

        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            try:
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            except Exception as exc:
                del sys.modules[mod_name]
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
                    f"Spider {obj.__name__} in {mod_name} failed validation: {exc}"
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
