import google.generativeai as genai

from bot.config import GEMINI_API_KEY


class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def summarize(self, title: str, description: str, url: str) -> str:
        content = f"Tiêu đề: {title}\nMô tả: {description}\nURL: {url}"
        prompt = (
            "Tóm tắt nội dung sau bằng tiếng Việt, ngắn gọn 3-5 câu. "
            "Bao gồm: chủ đề chính, điểm hay nhất, ai nên xem/đọc.\n"
            f"Nội dung: {content}"
        )
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text
            return ""
        except Exception:
            return ""
