import google.generativeai as genai

from bot.config import GEMINI_API_KEY


class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def summarize(self, title: str, description: str, url: str) -> str:
        content = f"Tieu de: {title}\nMo ta: {description}\nURL: {url}"
        prompt = (
            "Tom tat noi dung sau thanh tieng Viet, ngan gon 3-5 cau. "
            "Bao gom: chu de chinh, diem hay nhat, ai nen xem/doc.\n"
            f"Noi dung: {content}"
        )
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text
            return ""
        except Exception:
            return ""
