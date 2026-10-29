from cam_gpt_extractor import (
    CAMProvisionGPTExtractor,
    CAMStatementGPTParser,
    fill_prompt,
    parse_json_object,
)


def test_format_does_not_treat_cam_base_year_as_placeholder():
    try:
        CAMProvisionGPTExtractor.CAM_EXTRACTION_PROMPT.format(lease_text="Workday lease")
        raised = None
    except Exception as error:
        raised = error
    assert raised is not None
    assert "cam_base_year" in str(raised)


def test_fill_prompt_keeps_json_keys_and_inserts_lease():
    prompt = fill_prompt(
        CAMProvisionGPTExtractor.CAM_EXTRACTION_PROMPT,
        lease_text="CAM / Operating Cost Charges: Tenant pays increases over Base Year 2010",
    )
    assert '"cam_base_year"' in prompt
    assert "Base Year 2010" in prompt
    assert "{lease_text}" not in prompt


def test_fill_prompt_keeps_statement_json_example():
    prompt = fill_prompt(
        CAMStatementGPTParser.CAM_PARSING_PROMPT,
        statement_text="Utilities 12,000",
    )
    assert '"line_items"' in prompt
    assert "Utilities 12,000" in prompt
    assert "{statement_text}" not in prompt


def test_parse_json_object_accepts_fenced_payload():
    parsed = parse_json_object('```json\n{"cam_base_year": 2010, "has_cam_cap": false}\n```')
    assert parsed["cam_base_year"] == 2010
    assert parsed["has_cam_cap"] is False


if __name__ == "__main__":
    test_format_does_not_treat_cam_base_year_as_placeholder()
    test_fill_prompt_keeps_json_keys_and_inserts_lease()
    test_fill_prompt_keeps_statement_json_example()
    test_parse_json_object_accepts_fenced_payload()
    print("test_cam_gpt_extractor.py: all tests passed")
