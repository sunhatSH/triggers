from triggerctl import frontmatter


def test_parse_roundtrip():
    text = "---\nname: foo\nenabled: true\n---\n\n# Body\nhi\n"
    meta, body = frontmatter.parse(text)
    assert meta["name"] == "foo"
    assert meta["enabled"] is True
    assert "Body" in body


def test_no_frontmatter():
    meta, body = frontmatter.parse("# just markdown\n")
    assert meta == {}
    assert "just markdown" in body


def test_dump_then_parse():
    meta = {"name": "x", "enabled": False, "schedule": {"every": "day", "at": "14:30"}}
    out = frontmatter.dump(meta, "# hello")
    meta2, body2 = frontmatter.parse(out)
    assert meta2 == meta
    assert body2.strip() == "# hello"
