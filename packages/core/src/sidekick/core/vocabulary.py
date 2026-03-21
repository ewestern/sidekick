"""Controlled vocabulary for beat and geo routing keys.
"""

GEO_TREE: dict[str, dict[str, dict[str, set[str]]]] = {
    "us": {
        "ca": {
            "tulare": {"visalia"},
            "san_bernardino": {"san_bernardino"},
            "shasta": {"redding"},
        },
    },
}

BEAT_TREE: dict[str, dict[str, dict[str, set[str]]]] = {
    "government": {
        "city_council": {"budget"},
    },
    "education": {
        "school_board": {"budget"},
    },
    "housing_zoning": {
        "zoning_board": {"zoning_board"},
    },
    "public_safety": {
        "police": {"budget"},
    },
    "budget_finance": {
    },
}

def navigate_tree(
    tree: dict[str, dict[str, dict[str, set[str]]]], 
    id: str,
    error_format: str = "colon-separated segments"
) -> list[str]:
    """Navigate a hierarchical tree structure using a colon-delimited identifier.
    
    Args:
        tree: Nested dict structure (up to 4 levels deep).
        id: Colon-delimited identifier (e.g., "a:b:c" or "a:b:c:d").
        error_format: Custom error message format hint for better error messages.
    
    Returns:
        List of validated path segments.
    
    Raises:
        ValueError: If the identifier is invalid or not found in the tree.
    """
    parts = id.split(":")
    if not parts or not parts[0]:
        raise ValueError(f"Invalid id {id!r}. Expected {error_format}.")
    
    # Handle up to 4 segments safely
    first = parts[0]
    second = parts[1] if len(parts) > 1 else None
    third = parts[2] if len(parts) > 2 else None
    fourth = parts[3] if len(parts) > 3 else None
    
    if len(parts) > 4:
        raise ValueError(f"Invalid id {id!r}. Too many segments. Expected {error_format}.")
    
    node = tree.get(first)
    if node is None:
        raise ValueError(f"Invalid id {id!r}. First segment {first!r} not found. Expected {error_format}.")
    if second is None:
        return [first]
    node = node.get(second)
    if node is None:
        raise ValueError(f"Invalid id {id!r}. Second segment {second!r} not found under {first!r}. Expected {error_format}.")
    if third is None:
        return [first, second]
    node = node.get(third)
    if node is None:
        raise ValueError(f"Invalid id {id!r}. Third segment {third!r} not found under {first!r}:{second!r}. Expected {error_format}.")
    if fourth is None:
        return [first, second, third]
    if fourth not in node:
        raise ValueError(f"Invalid id {id!r}. Fourth segment {fourth!r} not found under {first!r}:{second!r}:{third!r}. Expected {error_format}.")
    return [first, second, third, fourth]


class GeoIdentifier:
    def __init__(self, geo_id: str):
        self.geo_id = geo_id
        self.parts = navigate_tree(GEO_TREE, geo_id, error_format="format: <country>:<state>:<county>:<city>")


    def __str__(self) -> str:
        return self.geo_id

    def __repr__(self) -> str:
        return f"GeoIdentifier({self.geo_id})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoIdentifier):
            return False
        return self.geo_id == other.geo_id


class BeatIdentifier:
    def __init__(self, beat_id: str):
        self.beat_id = beat_id
        self.parts = navigate_tree(BEAT_TREE, beat_id, error_format="format: <domain>:<subdomain>:<leaf>")

    def __str__(self) -> str:
        return self.beat_id

    def __repr__(self) -> str:
        return f"BeatIdentifier({self.beat_id})"


def validate_beat(beat: str) -> str:
    """Validate a beat identifier and return the canonical string form.
    
    Constructs a BeatIdentifier to validate against BEAT_TREE, then returns
    the canonical string representation for serialization.
    
    Args:
        beat: Beat identifier string (colon-delimited format).
    
    Returns:
        The validated beat identifier string.
    
    Raises:
        ValueError: If the beat identifier is invalid.
    """
    identifier = BeatIdentifier(beat)
    return str(identifier)


def validate_geo(geo: str) -> str:
    """Validate a geo identifier and return the canonical string form.
    
    Constructs a GeoIdentifier to validate against GEO_TREE, then returns
    the canonical string representation for serialization.
    
    Args:
        geo: Geo identifier string (colon-delimited format).
    
    Returns:
        The validated geo identifier string.
    
    Raises:
        ValueError: If the geo identifier is invalid.
    """
    identifier = GeoIdentifier(geo)
    return str(identifier)