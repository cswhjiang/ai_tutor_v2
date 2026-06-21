from __future__ import annotations

from conf.system import SYS_CONFIG


MATH_VIDEO_ROUTES = {"manimce", "fast", "manimgl"}


def normalize_math_video_route(value: object, *, default: str | None = None) -> str:
    """Return a normalized math-video route name."""
    if value is None:
        value = default
    route = str(value or "").strip().lower()
    if not route:
        route = default or SYS_CONFIG.math_video_generation_route
    if route not in MATH_VIDEO_ROUTES:
        raise ValueError(
            f"Unsupported math video route: {route}. "
            f"Expected one of: {', '.join(sorted(MATH_VIDEO_ROUTES))}."
        )
    return route


def _truthy(value: object) -> bool:
    """Return whether a JSON-like routing flag should be treated as enabled."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def resolve_math_video_route(current_parameters: dict) -> str:
    """
    Resolve the route for a math-video request.

    System configuration is the default. Explicit request fields still override
    the default so experiments can target a route without restarting the server.
    """
    if _truthy(current_parameters.get("use_manimce", False)):
        return "manimce"
    if _truthy(current_parameters.get("use_fast", False)):
        return "fast"

    requested_route = current_parameters.get("math_video_mode")
    if requested_route is None:
        requested_route = current_parameters.get("math_video_route")
    return normalize_math_video_route(
        requested_route,
        default=SYS_CONFIG.math_video_generation_route,
    )
