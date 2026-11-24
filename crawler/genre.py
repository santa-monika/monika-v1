"""Doan the loai game (danh muc v3 cua Monika) tu ten + mo ta tieng Anh. Quy tac tu khoa theo thu tu uu tien.
Chi la uoc luong: game khong khop quy tac nao vao 'Khác'. Mo ta goc chi dung de doan, khong dang."""
import re
from .normalize import strip_accents

# (ten danh muc v3, regex). Thu tu = uu tien.
RULES = [
    ("Kiếm hiệp & võ hiệp", r"wuxia|kung.?fu|shaolin|kiem hiep|tam quoc|three kingdoms|swordsman|martial arts? (hero|master|legend)"),
    ("Đua xe", r"\bracing\b|\brace\b|\brally\b|\bdrift|asphalt|need for speed|\bnfs\b|motocross|\bkart\b|formula|moto ?gp|\bdriv(e|er|ing)\b|turbo|car chase|burnout"),
    ("Thể thao", r"football|soccer|\bfifa\b|basketball|\bnba\b|tennis|\bgolf|baseball|cricket|rugby|hockey|bowling|billiard|snooker|\bpool\b|olympic|athletic|\bski|snowboard|surf|skate|fishing|volleyball|badminton|table tennis|\bpes\b|\bnfl\b|handball"),
    ("Đối kháng", r"fighting|kombat|street fighter|tekken|boxing|wrestl|\bwwe\b|\bufc\b|beat.?em|brawl|\bkof\b|king of fighters|\bfighter"),
    ("Bắn súng", r"shoot|sniper|\bguns?\b|\bfps\b|commando|counter.?strike|rifle|battlefield|call of duty|modern combat|mercenar|\bsoldier|\bsniper|\bgunman|\bgunship|\bsabotage|\bsiege\b|\bwar ?zone"),
    ("Sinh tồn & kinh dị", r"zombie|horror|survival|resident evil|silent hill|vampire|ghost|haunted|\bdead\b|dracula|nightmare|\bmonster|\bterror"),
    ("Thủ thành", r"tower defen[cs]e|defend (the|your)|\bplants? vs|\bdefense\b"),
    ("Chiến thuật", r"strateg|tactic|command (and|&) conquer|civilization|\bempire|\bconquer|\bwarfare|\bcommander|\barmy\b|rts\b|\bbattalion"),
    ("Cờ & bài", r"\bchess|checkers|solitaire|\bcards?\b|mahjong|domino|backgammon|reversi|othello|\buno\b|\bbridge\b|board game|\bgomoku|\bcaro\b|\bgo game|\bdraughts|chinese chess|\bluudo|\bludo"),
    ("Giải đố & trí tuệ", r"puzzle|match.?3|bubble|tetris|sudoku|\bbrain|\bword|crossword|\blogic|bejeweled|\bjewel|\bblocks?\b|\bmaze|\btiles?\b|\bquiz|trivia|\bmemory\b|\bconnect|\bcolumns\b|\bgems?\b|\bcandy|\bslide|\bmahjong"),
    ("Mô phỏng & quản lý", r"simulat|tycoon|\bmanager|\bfarm|\bsims?\b|restaurant|tamagotchi|\bhotel|\baquarium|\bgarden|\bcafe\b|\bcooking|\bkitchen"),
    ("Nhập vai", r"\brpg\b|role.?play|\bquest\b|dungeon|final fantasy|diablo|legend of|\bknight|\bwizard|\bmagic|fantasy|\bdragon|\bsword|\bhero(es)?\b|\bmedieval|\bsaga"),
    ("Phiêu lưu", r"adventure|explor|prince of persia|tomb raider|indiana|treasure|\bisland|\bjungle|\bescape|\bjourney|\bexpedition|\bmystery|\bdetective|\bpirates?\b|\bsecret"),
    ("Arcade & chạy nhảy", r"platform|\bjump|\brun(ner|ning)?\b|arcade|\brush\b|\bdash\b|jetpack|\bball\b|pac.?man|\bmario|\bsonic|\bbounce|\bclimb|\bflappy|\bsnake|\bbreakout|\bpinball|\binvader|\bshmup|\bpong"),
    ("Trẻ em & vui nhộn", r"\bkids?\b|children|cartoon|disney|smurf|sponge|\bdora\b|barbie|hello kitty|\bbaby\b|\bfunny|\bcute\b|\bbunny|\bpanda"),
    ("Hành động", r"\baction|assassin|crime|gangst|mafia|spider|batman|iron man|superhero|\bhitman|\bprison|\brescue|\bninja|\bmission|\bavengers|\bhulk|\bwolverine|\bmarvel|\bcop\b|\bpolice|\bheist|\bthief|\bcombat|\bterminator|\bagent|\bspy\b"),
]
_COMPILED = [(n, re.compile(r, re.I)) for n, r in RULES]
DEFAULT = "Khác"


# Mo ta tieng Anh rat nhieu tu chung chung (speed, war, tower...) nen chi tin cac cum tu the loai ro rang, trong 400 ky tu dau.
DESC_RULES = [
    ("Đua xe", r"racing game|race (against|your|through)|\brally\b|\bdrift"),
    ("Thể thao", r"football|soccer|basketball|\btennis|\bgolf|baseball|cricket|hockey|bowling|billiard|snooker|olympic|\bski(ing)?\b|snowboard|sports? game|fishing|volleyball|badminton"),
    ("Đối kháng", r"fighting game|\bbeat.?em|\bboxing|wrestl"),
    ("Bắn súng", r"shooter|shoot(ing)? (game|your|the|enemies)|sniper|\bfps\b"),
    ("Sinh tồn & kinh dị", r"zombie|horror|survival horror|\bvampire|haunted"),
    ("Thủ thành", r"tower defen[cs]e"),
    ("Chiến thuật", r"strategy game|real.?time strategy|turn.?based strategy|\btactical"),
    ("Cờ & bài", r"\bchess|checkers|solitaire|card game|mahjong|domino|backgammon|board game"),
    ("Giải đố & trí tuệ", r"puzzle|match.?3|\bbubble|tetris|sudoku|brain|crossword|\bquiz|trivia"),
    ("Mô phỏng & quản lý", r"simulat|tycoon|management game|\bfarm(ing)?\b|\brestaurant"),
    ("Nhập vai", r"\brpg\b|role.?playing|dungeon crawl"),
    ("Phiêu lưu", r"adventure game|\badventure\b"),
    ("Arcade & chạy nhảy", r"platform(er)? game|\barcade\b|endless runner|\brunner\b"),
    ("Trẻ em & vui nhộn", r"for kids|children"),
    ("Hành động", r"action game|action.?packed|\baction\b"),
]
_DESC = [(n, re.compile(r, re.I)) for n, r in DESC_RULES]


def guess_genre(title="", description=""):
    t = strip_accents(title or "").lower()
    d = strip_accents((description or "")[:400]).lower()
    for name, rx in _COMPILED:  # tieu de co trong so cao hon
        if rx.search(t):
            return name
    for name, rx in _DESC:
        if rx.search(d):
            return name
    return DEFAULT
