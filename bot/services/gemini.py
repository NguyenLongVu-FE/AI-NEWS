import google.generativeai as genai
import re
from urllib.parse import urlparse

from bot.config import GEMINI_API_KEY


class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def summarize(self, title: str, description: str, url: str) -> str:
        content = f"Tiêu đề: {title}\nMô tả: {description}\nURL: {url}"
        prompt = (
            "Tóm tắt nội dung sau bằng tiếng Việt theo đúng 4 gạch đầu dòng.\n"
            "Bắt buộc theo mẫu:\n"
            "• Chủ đề: ...\n"
            "• Nội dung chính: ...\n"
            "• URL xử lý gì: ...\n"
            "• Ai nên đọc: ...\n"
            "Mỗi dòng 1 ý rõ ràng, đầy đủ thông tin chính, không viết thành 1 đoạn.\n"
            f"Nội dung: {content}"
        )
        raw_summary = ""
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                raw_summary = response.text
        except Exception:
            raw_summary = ""
        return self.format_structured_summary(raw_summary, title, description, url)

    @staticmethod
    def _clean_text(value: str) -> str:
        compact = re.sub(r"\s+", " ", str(value or "")).strip()
        return compact.strip("-•* ").strip()

    @classmethod
    def _first_sentence(cls, value: str, fallback: str = "") -> str:
        compact = cls._clean_text(value)
        if not compact:
            compact = cls._clean_text(fallback)
        if not compact:
            return ""
        parts = [part.strip() for part in re.split(r"[.!?;]\s+|\n+", compact) if part.strip()]
        return parts[0] if parts else compact

    @staticmethod
    def _trim(value: str, max_len: int) -> str:
        compact = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3].rstrip() + "..."

    @classmethod
    def _extract_labeled_value(cls, raw_summary: str, labels: tuple[str, ...]) -> str:
        for line in str(raw_summary or "").splitlines():
            clean_line = cls._clean_text(line)
            lower = clean_line.lower()
            for label in labels:
                label_key = label.lower()
                if not lower.startswith(label_key):
                    continue
                value = clean_line[len(label):].strip(" :-")
                if value:
                    return value
        return ""

    @staticmethod
    def _infer_url_processing(text: str, domain: str) -> str:
        haystack = str(text or "").lower()
        if any(token in haystack for token in ("huong dan", "guide", "tutorial", "step")):
            return "Hướng dẫn cách triển khai và áp dụng theo từng bước."
        if any(token in haystack for token in ("so sanh", "compare", "benchmark")):
            return "So sánh các lựa chọn và nêu điểm mạnh/yếu để chọn nhanh."
        if any(token in haystack for token in ("checklist", "template", "plan", "roadmap")):
            return "Tổng hợp checklist/template để lập kế hoạch và thực thi nhanh."
        if any(token in haystack for token in ("case study", "thuc te", "kinh nghiem")):
            return "Phân tích case thực tế, cách làm và bài học rút ra."
        if domain:
            return f"Tổng hợp thông tin cốt lõi từ nguồn {domain} để áp dụng nhanh."
        return "Tổng hợp thông tin cốt lõi và cách áp dụng từ URL."

    @staticmethod
    def _infer_audience(text: str) -> str:
        haystack = str(text or "").lower()
        if any(token in haystack for token in ("ai agent", "agentic", "llm", "langgraph", "crewai")):
            return "Developer, PM và team đang xây AI Agent/automation."
        if any(token in haystack for token in ("react", "frontend", "ui", "ux", "css", "figma")):
            return "Frontend/UIUX và team sản phẩm cần triển khai nhanh."
        if any(token in haystack for token in ("marketing", "seo", "growth", "ads")):
            return "Team marketing/growth cần tối ưu hiệu quả thực thi."
        return "Người cần nắm nhanh nội dung chính để ra quyết định tiếp theo."

    @classmethod
    def format_structured_summary(
        cls, raw_summary: str, title: str, description: str, url: str
    ) -> str:
        domain = (urlparse(str(url or "")).netloc or "").lower().removeprefix("www.")
        combined = " ".join(
            item for item in [raw_summary, description, title] if str(item or "").strip()
        )

        topic = cls._extract_labeled_value(raw_summary, ("Chủ đề", "Topic"))
        if not topic:
            topic = cls._first_sentence(title, fallback=combined)
        if not topic:
            topic = "Nội dung từ URL"

        main = cls._extract_labeled_value(raw_summary, ("Nội dung chính", "Noi dung chinh"))
        if not main:
            main = cls._first_sentence(raw_summary, fallback=description)
        if not main:
            main = "Tổng hợp các ý chính quan trọng từ nội dung URL."

        url_processing = cls._extract_labeled_value(raw_summary, ("URL xử lý gì", "URL xu ly gi"))
        if not url_processing:
            url_processing = cls._infer_url_processing(combined, domain)

        audience = cls._extract_labeled_value(raw_summary, ("Ai nên đọc", "Ai nen doc"))
        if not audience:
            audience = cls._infer_audience(combined)

        lines = [
            f"• Chủ đề: {cls._trim(topic, 120)}",
            f"• Nội dung chính: {cls._trim(main, 220)}",
            f"• URL xử lý gì: {cls._trim(url_processing, 220)}",
            f"• Ai nên đọc: {cls._trim(audience, 160)}",
        ]
        return "\n".join(lines)
