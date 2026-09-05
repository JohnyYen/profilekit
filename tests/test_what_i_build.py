"""Tests for generators.utils.what_i_build — platform variant fallback logic."""

import pytest


# ---------------------------------------------------------------------------
# (a) variant present for platform → returns variant value wrapped in list
# ---------------------------------------------------------------------------

def test_what_i_build_returns_platform_variant():
    """When whatIBuildVariants[platform] is present, return it."""
    from generators.utils import what_i_build

    about = {
        "whatIBuildVariants": {"github": "Type-safe backend templates."},
        "whatIBuild": ["Generic item"],
    }
    result = what_i_build(about, "github")
    assert result == ["Type-safe backend templates."]


# ---------------------------------------------------------------------------
# (b) variant key absent for platform → returns whatIBuild list
# ---------------------------------------------------------------------------

def test_what_i_build_falls_back_when_platform_key_absent():
    """When the platform key is absent from whatIBuildVariants, return whatIBuild."""
    from generators.utils import what_i_build

    about = {
        "whatIBuildVariants": {"linkedin": "Some LinkedIn text."},
        "whatIBuild": ["APIs", "Boilerplates"],
    }
    result = what_i_build(about, "github")
    assert result == ["APIs", "Boilerplates"]


# ---------------------------------------------------------------------------
# (c) whatIBuildVariants absent → returns whatIBuild
# ---------------------------------------------------------------------------

def test_what_i_build_falls_back_when_variants_absent():
    """When whatIBuildVariants is entirely absent, return whatIBuild."""
    from generators.utils import what_i_build

    about = {"whatIBuild": ["APIs", "Templates"]}
    result = what_i_build(about, "github")
    assert result == ["APIs", "Templates"]


# ---------------------------------------------------------------------------
# (d) variant is null → returns whatIBuild
# ---------------------------------------------------------------------------

def test_what_i_build_falls_back_when_variant_is_null():
    """When whatIBuildVariants[platform] is null, fall back to whatIBuild."""
    from generators.utils import what_i_build

    about = {
        "whatIBuildVariants": {"github": None},
        "whatIBuild": ["Fallback item"],
    }
    result = what_i_build(about, "github")
    assert result == ["Fallback item"]


# ---------------------------------------------------------------------------
# (e) both absent → returns []
# ---------------------------------------------------------------------------

def test_what_i_build_returns_empty_list_when_both_absent():
    """When neither whatIBuildVariants nor whatIBuild is present, return []."""
    from generators.utils import what_i_build

    about = {"username": "testuser"}
    result = what_i_build(about, "github")
    assert result == []
