import pytest

from src.backend.kwin.layout import (
    calculate_geometry,
    find_output,
    get_quick_tile,
)


@pytest.fixture
def three_outputs():
    return [
        {
            "name": "DP-1",
            "x": -1920,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "enabled": True,
        },
        {
            "name": "HDMI-A-1",
            "x": 0,
            "y": -120,
            "width": 2560,
            "height": 1440,
            "enabled": True,
        },
        {
            "name": "DP-2",
            "x": 2560,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "enabled": True,
        },
    ]


@pytest.mark.parametrize(
    ("tile", "expected"),
    [
        ("full", {"x": 100, "y": 50, "width": 1000, "height": 800}),
        ("max", {"x": 100, "y": 50, "width": 1000, "height": 800}),
        ("left", {"x": 100, "y": 50, "width": 500, "height": 800}),
        ("right", {"x": 600, "y": 50, "width": 500, "height": 800}),
        ("top", {"x": 100, "y": 50, "width": 1000, "height": 400}),
        ("bottom", {"x": 100, "y": 450, "width": 1000, "height": 400}),
        ("top-left", {"x": 100, "y": 50, "width": 500, "height": 400}),
        (
            "bottom-right",
            {"x": 600, "y": 450, "width": 500, "height": 400},
        ),
    ],
)
def test_calculate_geometry_for_presets(tile, expected):
    output = {"x": 100, "y": 50, "width": 1000, "height": 800}

    assert calculate_geometry(output, tile) == expected


@pytest.mark.parametrize(
    "tile",
    ["TOP LEFT", "top_left", "north-west", "northwest", "nw"],
)
def test_tile_aliases_are_normalised(tile):
    output = {"x": 0, "y": 0, "width": 1200, "height": 800}

    assert calculate_geometry(output, tile) == {
        "x": 0,
        "y": 0,
        "width": 600,
        "height": 400,
    }


@pytest.mark.parametrize(
    "tile",
    [
        {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.75},
        [0.25, 0.1, 0.5, 0.75],
    ],
)
def test_calculate_geometry_accepts_custom_tiles(tile):
    output = {"x": -100, "y": 20, "width": 1000, "height": 800}

    assert calculate_geometry(output, tile) == {
        "x": 150,
        "y": 100,
        "width": 500,
        "height": 600,
    }

def test_geometry_uses_edges_to_avoid_rounding_gaps():
    output = {"x": 0, "y": 0, "width": 101, "height": 99}

    left = calculate_geometry(output, [0, 0, 0.5, 1])
    right = calculate_geometry(output, [0.5, 0, 0.5, 1])

    assert left["x"] + left["width"] == right["x"]
    assert right["x"] + right["width"] == 101


@pytest.mark.parametrize(
    ("tile", "error"),
    [
        ("diagonal", ValueError),
        ([0, 0, 1], ValueError),
        ([0, 0, "wide", 1], ValueError),
        ([-0.1, 0, 0.5, 1], ValueError),
        ([0, 0, 0, 1], ValueError),
        ([0, 0, 1.1, 1], ValueError),
        ({"x": 0, "y": 0, "width": 1}, ValueError),
    ],
)
def test_invalid_tiles_are_rejected(tile, error):
    with pytest.raises(error):
        calculate_geometry(
            {"x": 0, "y": 0, "width": 100, "height": 100},
            tile,
        )


@pytest.mark.parametrize(
    ("tile", "expected"),
    [
        ("left", "left"),
        (" LEFT ", "left"),
        ("north east", "top-right"),
        ("se", "bottom-right"),
        ("full", None),
        ("max", None),
        ([0, 0, 0.5, 1], None),
    ],
)
def test_get_quick_tile(tile, expected):
    assert get_quick_tile(tile) == expected


def test_find_output_prefers_exact_physical_name(three_outputs):
    assert find_output(three_outputs, "DP-2")["name"] == "DP-2"


def test_find_output_matches_physical_name_case_insensitively(three_outputs):
    assert find_output(three_outputs, "hdmi-a-1")["name"] == "HDMI-A-1"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("left", "DP-1"),
        ("west", "DP-1"),
        ("center", "HDMI-A-1"),
        ("centre", "HDMI-A-1"),
        ("rightmost", "DP-2"),
        ("east", "DP-2"),
    ],
)
def test_find_output_resolves_logical_names(three_outputs, name, expected):
    assert find_output(three_outputs, name)["name"] == expected


def test_disabled_outputs_are_ignored():
    outputs = [
        {"name": "off", "x": -100, "y": 0, "width": 100, "height": 100,
         "enabled": False},
        {"name": "on", "x": 0, "y": 0, "width": 100, "height": 100},
    ]

    assert find_output(outputs, "left")["name"] == "on"


def test_find_output_reports_available_names(three_outputs):
    with pytest.raises(RuntimeError) as error:
        find_output(three_outputs, "projector")

    message = str(error.value)
    assert "projector" in message
    assert "DP-1" in message
    assert "DP-2" in message
    assert "HDMI-A-1" in message


def test_find_output_rejects_empty_enabled_set():
    with pytest.raises(RuntimeError, match="no enabled outputs"):
        find_output(
            [{"name": "DP-1", "enabled": False}],
            "left",
        )


@pytest.mark.parametrize("key", ["x", "y", "width", "height"])
def test_geometry_requires_all_output_dimensions(key):
    output = {"x": 0, "y": 0, "width": 100, "height": 100}
    del output[key]

    with pytest.raises(RuntimeError, match=f"missing '{key}'"):
        calculate_geometry(output, "full")


def test_geometry_rejects_non_numeric_output_dimension():
    with pytest.raises(RuntimeError, match="is not numeric"):
        calculate_geometry(
            {"x": 0, "y": 0, "width": "wide", "height": 100},
            "full",
        )
