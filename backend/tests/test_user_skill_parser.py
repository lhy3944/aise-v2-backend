import pytest

from src.core.exceptions import AppException
from src.services.user_skill_svc import parse_markdown_skill


def test_parse_markdown_skill_uses_frontmatter_name_and_description():
    draft = parse_markdown_skill(
        "---\nname: strict-review\ndescription: Review with strict criteria\n---\n# Rules\nBe concise.",
        source_type="text",
    )

    assert draft.name == "strict-review"
    assert draft.description == "Review with strict criteria"
    assert draft.body == "# Rules\nBe concise."
    assert draft.source_type == "text"
    assert draft.content_hash


def test_parse_markdown_skill_falls_back_to_title_and_description():
    draft = parse_markdown_skill(
        "# My Skill\nAlways answer in Korean.",
        source_type="upload",
        fallback_name="Uploaded skill",
        fallback_description="From a markdown file",
    )

    assert draft.name == "Uploaded skill"
    assert draft.description == "From a markdown file"
    assert draft.body == "# My Skill\nAlways answer in Korean."


def test_parse_markdown_skill_rejects_empty_body():
    with pytest.raises(AppException) as exc:
        parse_markdown_skill("   ", source_type="text")

    assert exc.value.status_code == 400


def test_parse_markdown_skill_rejects_invalid_frontmatter():
    with pytest.raises(AppException) as exc:
        parse_markdown_skill("---\nname strict-review\n---\nBody", source_type="text")

    assert exc.value.status_code == 400
