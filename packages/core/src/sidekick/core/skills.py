"""Skill file loader — framework-agnostic disk reader for agent skills.

Skills live in the repo under skills/{skill_id}/ containing SKILL.md and
optional references/ subdirectory. Call load_skills_from_disk() with a list
of skill IDs (from ResolvedAgentConfig.skills) to get a path → content mapping
that can be loaded into any agent framework's store.

Each service that uses DeepAgents wraps this function to populate an
InMemoryStore (or other BaseStore) using create_file_data from deepagents.
"""

from __future__ import annotations

from pathlib import Path


def load_skills_from_disk(
    skill_ids: list[str],
    skills_dir: Path,
) -> dict[str, str]:
    """Read named skill directories and return a {path: content} mapping.

    Each skill_id corresponds to a directory under skills_dir/ containing
    SKILL.md and optional references/ files. Keys use POSIX-style paths like
    "/skills/news-values/SKILL.md" so they can be stored directly in a
    DeepAgents StoreBackend without further transformation.

    Args:
        skill_ids: List of skill directory names (e.g. ["news-values", "government-proceedings"]).
        skills_dir: Root directory containing skill subdirectories.

    Returns:
        Dict mapping "/skills/{skill_id}/..." paths to file contents.

    Raises:
        FileNotFoundError: If any skill_id directory does not exist under skills_dir.
    """
    files: dict[str, str] = {}
    for skill_id in skill_ids:
        skill_path = skills_dir / skill_id
        if not skill_path.is_dir():
            raise FileNotFoundError(
                f"Skill directory not found: {skill_path}. "
                f"Check that '{skill_id}' exists under {skills_dir}."
            )
        for file_path in sorted(skill_path.rglob("*")):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(skills_dir)
            key = f"/skills/{relative.as_posix()}"
            files[key] = file_path.read_text(encoding="utf-8")
    return files
