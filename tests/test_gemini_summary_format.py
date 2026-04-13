from bot.services.gemini import GeminiService


def test_format_structured_summary_always_returns_four_bullet_lines():
    summary = GeminiService.format_structured_summary(
        raw_summary="Bai viet huong dan xay dung AI agent workflow voi LangGraph.",
        title="AI Agent workflow",
        description="Mo ta tong quan ve skill plan va tool calling.",
        url="https://example.com/ai-agent",
    )

    lines = summary.splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("• Chủ đề:")
    assert lines[1].startswith("• Nội dung chính:")
    assert lines[2].startswith("• URL xử lý gì:")
    assert lines[3].startswith("• Ai nên đọc:")


def test_format_structured_summary_respects_labeled_ai_output():
    summary = GeminiService.format_structured_summary(
        raw_summary=(
            "• Chủ đề: AI Agent skill plan\n"
            "• Nội dung chính: Huong dan thiet ke quy trinh lap ke hoach.\n"
            "• URL xử lý gì: Chuyen hoa yeu cau thanh plan de trien khai.\n"
            "• Ai nên đọc: Team dev va PM."
        ),
        title="Fallback title",
        description="Fallback desc",
        url="https://example.com/skill-plan",
    )

    assert "• Chủ đề: AI Agent skill plan" in summary
    assert "• URL xử lý gì: Chuyen hoa yeu cau thanh plan de trien khai." in summary
    assert "• Ai nên đọc: Team dev va PM." in summary


def test_format_structured_summary_builds_fallback_when_raw_is_empty():
    summary = GeminiService.format_structured_summary(
        raw_summary="",
        title="Cap nhat he thong",
        description="",
        url="https://news.example.com/update",
    )

    assert "• Chủ đề: Cap nhat he thong" in summary
    assert "• URL xử lý gì: Tổng hợp thông tin cốt lõi từ nguồn news.example.com để áp dụng nhanh." in summary
