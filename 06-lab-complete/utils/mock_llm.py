"""
Mock History Tutor LLM

Đề tài Part 6: AI agent giúp học sinh học lịch sử.
Không gọi API thật — trả lời giả lập để tập trung vào deployment concepts.
"""

from __future__ import annotations

import random
import time


HISTORY_RULES = [
    "Trả lời ngắn gọn, dễ hiểu, phù hợp học sinh.",
    "Nếu câu hỏi mơ hồ, hỏi lại 1 câu để làm rõ.",
    "Luôn gợi ý 1-2 ý để học tiếp (mốc thời gian, nhân vật, nguyên nhân-kết quả).",
]

MOCK_KB = {
    "default": [
        "Mình giúp bạn học lịch sử nhé. Bạn muốn tìm hiểu giai đoạn nào (cổ đại, trung đại, cận-hiện đại) và khu vực nào (Việt Nam/thế giới)?",
        "Đây là câu trả lời từ AI tutor lịch sử (mock). Nếu bạn cho mình thêm bối cảnh (lớp mấy, bài nào) mình giải thích sát hơn.",
    ],
    "chien_tranh": [
        "Khi học về chiến tranh, hãy nhớ 3 ý: nguyên nhân → diễn biến chính → kết quả/ý nghĩa. Bạn đang hỏi về cuộc chiến nào?",
    ],
    "viet_nam": [
        "Lịch sử Việt Nam có thể chia theo các mốc lớn: dựng nước, thời phong kiến, thời cận-hiện đại. Bạn muốn bắt đầu từ mốc nào?",
    ],
    "cach_mang": [
        "Cách mạng thường có 4 phần: bối cảnh, lực lượng tham gia, sự kiện then chốt, ý nghĩa. Bạn đang học cách mạng nào?",
    ],
    "on_tap": [
        "Gợi ý ôn tập: lập timeline 5 mốc, mỗi mốc 1 câu 'vì sao quan trọng'. Bạn muốn mình tạo timeline cho chủ đề nào?",
    ],
}


def ask(question: str, delay: float = 0.08) -> str:
    """Trả lời giả lập theo từ khóa lịch sử."""
    time.sleep(delay + random.uniform(0, 0.05))

    q = (question or "").lower()

    if any(k in q for k in ["việt nam", "vietnam", "đại việt", "nhà", "triều"]):
        base = random.choice(MOCK_KB["viet_nam"])
    elif any(k in q for k in ["chiến tranh", "war", "trận", "xâm lược"]):
        base = random.choice(MOCK_KB["chien_tranh"])
    elif any(k in q for k in ["cách mạng", "revolution", "khởi nghĩa"]):
        base = random.choice(MOCK_KB["cach_mang"])
    elif any(k in q for k in ["ôn", "tóm tắt", "timeline", "ghi nhớ"]):
        base = random.choice(MOCK_KB["on_tap"])
    else:
        base = random.choice(MOCK_KB["default"])

    rule = random.choice(HISTORY_RULES)
    return f"{base}\n\nGợi ý học: {rule}"

