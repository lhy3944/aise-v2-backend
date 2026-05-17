import pytest

from src.services import user_skill_svc


@pytest.mark.asyncio
async def test_save_skill_reactivates_existing_content_hash(db):
    draft = user_skill_svc.parse_markdown_skill(
        "---\nname: qa-style\ndescription: QA style\n---\nPrefer edge cases.",
        source_type="text",
    )

    created = await user_skill_svc.save_skill(db, draft, owner_id="tester")
    await user_skill_svc.update_skill(db, created.id, owner_id="tester", enabled=False)

    duplicate = await user_skill_svc.save_skill(db, draft, owner_id="tester")

    assert duplicate.id == created.id
    assert duplicate.enabled is True


@pytest.mark.asyncio
async def test_format_enabled_skill_instructions_includes_only_enabled_skills(db):
    enabled = user_skill_svc.parse_markdown_skill(
        "---\nname: enabled-style\ndescription: Enabled\n---\nUse tables for comparisons.",
        source_type="text",
    )
    disabled = user_skill_svc.parse_markdown_skill(
        "---\nname: disabled-style\ndescription: Disabled\n---\nThis should not appear.",
        source_type="text",
    )

    await user_skill_svc.save_skill(db, enabled, owner_id="tester")
    saved_disabled = await user_skill_svc.save_skill(db, disabled, owner_id="tester")
    await user_skill_svc.update_skill(db, saved_disabled.id, owner_id="tester", enabled=False)

    instructions = await user_skill_svc.format_enabled_skill_instructions(db, owner_id="tester")

    assert "enabled-style" in instructions
    assert "Use tables for comparisons." in instructions
    assert "disabled-style" not in instructions
    assert "This should not appear." not in instructions
