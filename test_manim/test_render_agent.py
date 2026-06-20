import os

from src.agents.experts.math_video.render_agent import (
    LEGACY_BYTEDANCE_IMPORT,
    LOCAL_BYTEDANCE_IMPORT,
    PROJECT_ROOT,
    build_manim_subprocess_env,
    normalize_manim_voiceover_imports,
)


def test_normalize_manim_voiceover_imports_uses_project_local_bytedance_service():
    code = f"""
from manim import *
{LEGACY_BYTEDANCE_IMPORT}
"""

    normalized = normalize_manim_voiceover_imports(code)

    assert LOCAL_BYTEDANCE_IMPORT in normalized
    assert LEGACY_BYTEDANCE_IMPORT not in normalized


def test_build_manim_subprocess_env_prepends_project_root_to_pythonpath():
    existing_path = "/tmp/example_pythonpath"
    env = build_manim_subprocess_env({"PYTHONPATH": existing_path})
    paths = env["PYTHONPATH"].split(os.pathsep)

    assert paths[0] == str(PROJECT_ROOT)
    assert existing_path in paths


def test_build_manim_subprocess_env_deduplicates_project_root():
    existing_path = "/tmp/example_pythonpath"
    env = build_manim_subprocess_env(
        {"PYTHONPATH": os.pathsep.join([existing_path, str(PROJECT_ROOT)])}
    )
    paths = env["PYTHONPATH"].split(os.pathsep)

    assert paths.count(str(PROJECT_ROOT)) == 1
