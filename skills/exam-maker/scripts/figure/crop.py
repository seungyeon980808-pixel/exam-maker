# 원본 재활용: 교과서·학습지·기출 PDF(또는 쪽 그림)에서 그림 부분만 잘라 PNG로 저장한다.
# 실행:
#   python crop.py page  <자료.pdf> <쪽번호> <출력.png> [--dpi 200]              # 쪽 전체를 그림으로(자를 곳을 눈으로 고를 때)
#   python crop.py crop  <자료.pdf> <쪽번호> <x0> <y0> <x1> <y1> <출력.png>       # 쪽 안 비율 좌표(0~1)로 잘라내기
#   python crop.py imgs  <자료.pdf> <쪽번호> <출력폴더>                            # 쪽에 박힌 그림 파일을 그대로 꺼내기
#   python crop.py gray  <그림.png> <출력.png>                                     # 흑백으로(시험지는 흑백 인쇄)
# 필요: pip install pymupdf pillow
import sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path


def need():
    try:
        import pymupdf  # noqa
        return pymupdf
    except ImportError:
        sys.exit("pymupdf가 없습니다: python -m pip install pymupdf pillow")


def main(a):
    if not a:
        sys.exit(__doc__ or "사용법은 파일 맨 위 주석을 보세요.")
    cmd = a[0]
    if cmd == "gray":
        from PIL import Image
        Image.open(a[1]).convert("L").save(a[2]); print("흑백:", a[2]); return
    fitz = need()
    doc = fitz.open(a[1]); pg = doc[int(a[2]) - 1]
    if cmd == "page":
        dpi = int(a[5]) if len(a) > 5 and a[4] == "--dpi" else 150
        pg.get_pixmap(dpi=dpi).save(a[3]); print("쪽 그림:", a[3])
    elif cmd == "crop":
        x0, y0, x1, y1 = map(float, a[3:7]); r = pg.rect
        clip = fitz.Rect(r.x0 + r.width * x0, r.y0 + r.height * y0, r.x0 + r.width * x1, r.y0 + r.height * y1)
        pg.get_pixmap(dpi=300, clip=clip).save(a[7]); print("잘라냄:", a[7])
    elif cmd == "imgs":
        out = Path(a[3]); out.mkdir(parents=True, exist_ok=True)
        for i, info in enumerate(pg.get_images(full=True), 1):
            pix = fitz.Pixmap(doc, info[0])
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            p = out / f"p{a[2]}_img{i}.png"; pix.save(str(p)); print(p)
    else:
        sys.exit("명령은 page | crop | imgs | gray")


if __name__ == "__main__":
    main(sys.argv[1:])
