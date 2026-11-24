"""Sinh mo ta tieng Viet tu du lieu co cau truc (the loai, hang, do phan giai, dung luong). Khong chep mo ta cua nguon.
Moi game chon bien the cau theo ma bam id de cac bai khong giong het nhau."""
import zlib

GENRE_SHORT = {
    "Hành động": "hành động", "Phiêu lưu": "phiêu lưu", "Nhập vai": "nhập vai", "Kiếm hiệp & võ hiệp": "kiếm hiệp",
    "Chiến thuật": "chiến thuật", "Thủ thành": "thủ thành", "Đua xe": "đua xe", "Thể thao": "thể thao", "Bắn súng": "bắn súng",
    "Đối kháng": "đối kháng", "Giải đố & trí tuệ": "giải đố", "Arcade & chạy nhảy": "arcade", "Mô phỏng & quản lý": "mô phỏng",
    "Cờ & bài": "cờ và bài", "Sinh tồn & kinh dị": "sinh tồn và kinh dị", "Trẻ em & vui nhộn": "vui nhộn", "Khác": "giải trí",
}
BLURB = {
    "Hành động": ["Nhân vật di chuyển, chiến đấu và hoàn thành nhiệm vụ qua từng màn.", "Thiên về phản xạ và nhịp độ nhanh, hợp lúc muốn chơi giải trí ngắn."],
    "Phiêu lưu": ["Người chơi khám phá, vượt chướng ngại và đi tiếp theo mạch cốt truyện.", "Chơi chậm rãi hơn, thiên về khám phá màn chơi."],
    "Nhập vai": ["Nhân vật lớn dần theo từng chặng, có nhiệm vụ và trang bị để nâng cấp.", "Hợp người thích chơi dài hơi, cày cấp và theo cốt truyện."],
    "Kiếm hiệp & võ hiệp": ["Bối cảnh võ thuật, nhân vật luyện chiêu và đối đầu qua từng màn.", "Hợp người mê truyện kiếm hiệp và võ thuật."],
    "Chiến thuật": ["Cần tính toán lực lượng và nước đi trước khi ra quân.", "Chơi theo lượt hoặc thời gian thực, thiên về suy nghĩ hơn là phản xạ."],
    "Thủ thành": ["Đặt phòng thủ để chặn các đợt tấn công liên tiếp.", "Nhịp chơi vừa phải, càng về sau càng cần tính toán vị trí."],
    "Đua xe": ["Điều khiển xe vượt qua các đường đua và bứt lên trên các đối thủ.", "Thiên về tốc độ và né chướng ngại."],
    "Thể thao": ["Mô phỏng môn thể thao với luật chơi đơn giản, dễ làm quen.", "Có thể chơi nhanh từng trận hoặc theo giải."],
    "Bắn súng": ["Ngắm và bắn để vượt qua từng màn.", "Cần phản xạ và canh đúng thời điểm."],
    "Đối kháng": ["Hai bên giao đấu bằng đòn đánh và combo.", "Hợp chơi giải trí nhanh từng trận."],
    "Giải đố & trí tuệ": ["Cần quan sát và suy nghĩ để qua từng màn.", "Nhịp chậm, hợp lúc muốn thư giãn."],
    "Arcade & chạy nhảy": ["Cách chơi đơn giản, dễ vào nhưng khó dừng.", "Thiên về phản xạ và ghi điểm cao."],
    "Mô phỏng & quản lý": ["Người chơi tự điều hành, xây dựng và phát triển dần.", "Nhịp chơi thong thả, thiên về sắp xếp và quản lý."],
    "Cờ & bài": ["Luật chơi quen thuộc, có thể chơi một mình với máy.", "Hợp giải trí ngắn lúc rảnh."],
    "Sinh tồn & kinh dị": ["Không khí căng thẳng, cần sống sót qua từng màn.", "Thiên về hồi hộp, cần thao tác nhanh."],
    "Trẻ em & vui nhộn": ["Cách chơi nhẹ nhàng, hình ảnh vui mắt.", "Dễ chơi, hợp giải trí ngắn."],
    "Khác": ["Game Java giải trí chạy trên máy phím bấm.", "Cách chơi đơn giản, hợp máy cấu hình thấp."],
}
INTRO = ["{t} là game {g}{v} dành cho máy Java.", "{t}: game {g}{v} chạy trên điện thoại Java.", "Game {g} {t}{v} cho máy phím bấm Java."]


def _pick(seq, gid, salt=0):
    return seq[(zlib.crc32(f"{gid}:{salt}".encode()) + salt) % len(seq)]


def describe(g, genre, res_list, kb_min, kb_max):
    """Tra ve (desc <=120 ky tu, body). res_list da sap theo do pho bien."""
    gid = g["source_id"]
    vend = f" của {g['vendor']}" if g.get("vendor") else ""
    gs = GENRE_SHORT.get(genre, "giải trí")
    intro = _pick(INTRO, gid).format(t=g["title"], g=gs, v=vend)
    blurb = _pick(BLURB[genre], gid, 1)
    k = len(res_list)
    top = ", ".join(res_list[:3])
    size = f"{kb_min} KB" if kb_min and kb_min == kb_max else (f"{kb_min}–{kb_max} KB" if kb_min else "")
    facts = f"Có bản cho {k} độ phân giải màn hình, phổ biến nhất: {top}." if k else "Chưa rõ độ phân giải."
    if size:
        facts += f" Dung lượng khoảng {size}."
    desc = f"Game {gs}{vend} cho máy Java, có {k} độ phân giải" + (f", từ {size}" if size else "") + "."
    if len(desc) > 120:
        desc = f"Game {gs} cho máy Java, có {k} độ phân giải."
    return desc[:120], f"{intro} {blurb} {facts}"
