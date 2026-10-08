"""Non-colliding top-level package name (spec `package-distribution`, Req:
Non-colliding top-level package name).

The distributed package must not ship a top-level module named `generators`
(too generic, collides with the retired internal name) and must be
importable under its new, project-specific name: `profilekit`.
"""

import importlib.util


def test_profilekit_is_importable():
    spec = importlib.util.find_spec("profilekit")
    assert spec is not None, "the installed package must expose a 'profilekit' module"


def test_no_top_level_generators_module_ships():
    spec = importlib.util.find_spec("generators")
    assert spec is None, "no top-level 'generators' module must ship"
