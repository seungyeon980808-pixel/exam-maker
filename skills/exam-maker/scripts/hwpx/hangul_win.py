# -*- coding: utf-8 -*-
"""윈도우 전용: 설치된 한글(한컴오피스)을 자동으로 움직여 파일을 바꾸고 쪽 그림을 만든다.

    python hangul_win.py to-hwpx 양식.hwp 양식.hwpx      학교가 준 옛 hwp 양식을 hwpx로
    python hangul_win.py to-pdf  시험지.hwpx 시험지.pdf   한글이 조판한 그대로 PDF로
    python hangul_win.py pages   시험지.hwpx 쪽그림폴더   PDF로 저장한 뒤 쪽마다 PNG(page-1.png …) — Claude가 눈으로 확인
    python hangul_win.py open    시험지.hwpx             한글로 열기(사람이 마지막 조판을 손봄)

준비물
  - 한글 2018 이상(한컴오피스). 한글 자동화(HWPFrame.HwpObject)가 함께 설치된다.
  - pip install pyhwpx          (권장: 아래 보안 모듈을 스스로 등록해 준다. 안에 pywin32 가 딸려 온다)
    또는 pip install pywin32    (pyhwpx 없이 쓸 때)
  - pages 를 쓰려면 pip install pymupdf

보안 모듈(파일 접근 승인 창)
  한글은 다른 프로그램이 파일을 열거나 저장하려 하면 「한글을 이용하여 위 파일에 접근하려는 시도…」 창을 띄우고
  사람이 「접근 허용」을 눌러야 계속한다. 이 창을 매번 안 보려면 보안 모듈을 등록한다.
  1) pyhwpx 를 설치하면 처음 Hwp()를 만들 때 보안 모듈 DLL 을 스스로 등록한다(가장 쉬움).
  2) 손으로 할 때: 한컴디벨로퍼(developer.hancom.com)의 「한/글 오토메이션 보안 모듈」(FilePathCheckerModule*.dll)을
     받아 둔 뒤, 레지스트리 HKEY_CURRENT_USER\\Software\\HNC\\HwpAutomation\\Modules 에
     문자열 값 이름 FilePathCheckerModule, 값 = DLL 전체 경로 를 만든다. 이 스크립트는 레지스트리를 고치지 않는다.
  등록이 안 되어 있어도 동작은 한다. 창이 뜨면 「모두 허용」을 누르면 된다.

이 파일은 맥에서 시험할 수 없어 한컴 공식 자동화 API 이름(Open·SaveAs·RegisterModule·XHwpWindows·PageCount·Clear·Quit)만 쓴다.
"""
from __future__ import annotations

import os
import sys

if sys.platform != "win32":
    _MSG = ("hangul_win.py 는 윈도우에서 한글(한컴오피스)이 설치된 컴퓨터에서만 씁니다.\n"
            "맥·리눅스에서는 build_exam.py 로 hwpx 를 만든 뒤, 윈도우 컴퓨터의 한글에서 열거나\n"
            "그 컴퓨터에서 python hangul_win.py pages 시험지.hwpx 쪽그림 으로 쪽 그림을 만드세요.")
    if __name__ == "__main__":
        print(_MSG)
        sys.exit(2)
    raise ImportError(_MSG)

import argparse  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402


def _console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


class HangulError(RuntimeError):
    pass


class Hangul:
    """한글 자동화 객체. with 로 쓰면 끝날 때 문서를 닫고 한글을 끈다.
    pyhwpx 가 있으면 그것으로 만들고(보안 모듈 자동 등록), 실제 호출은 한컴 공식 COM API 로 한다."""

    def __init__(self, visible=False):
        self.visible = visible
        self.com = None
        self._py = None
        self.via = ""

    def __enter__(self):
        err = []
        try:
            from pyhwpx import Hwp  # type: ignore
            try:
                self._py = Hwp(visible=self.visible)
            except TypeError:  # 판에 따라 인자 이름이 다를 수 있다
                self._py = Hwp()
            com = getattr(self._py, "hwp", None)   # pyhwpx 안의 실제 COM 객체
            if com is not None and hasattr(com, "Open"):
                self.com = com
                self.via = "pyhwpx"
            else:
                err.append("pyhwpx 에서 COM 객체를 찾지 못함")
                try:
                    self._py.quit()
                except Exception:
                    pass
                self._py = None
        except ImportError:
            err.append("pyhwpx 없음")
        except Exception as e:  # pyhwpx 는 있는데 한글을 못 띄움
            err.append("pyhwpx 로 한글을 띄우지 못함: %s" % e)
        if self.com is None:
            try:
                import win32com.client  # type: ignore
            except ImportError:
                raise HangulError("pyhwpx 도 pywin32 도 없습니다. 먼저  pip install pyhwpx  를 실행하세요.\n(%s)" % "; ".join(err))
            try:
                self.com = win32com.client.Dispatch("HWPFrame.HwpObject")
                self.via = "win32com"
            except Exception as e:
                raise HangulError("한글 자동화 객체(HWPFrame.HwpObject)를 만들지 못했습니다. 한글(한컴오피스)이 설치되어 있는지, "
                                  "한 번이라도 실행해 정품 인증을 마쳤는지 확인하세요.\n원인: %s" % e)
            try:  # 보안 모듈이 레지스트리에 등록되어 있으면 승인 창 없이 진행된다(없으면 False, 그래도 계속)
                ok = self.com.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
                if not ok:
                    print("[알림] 보안 모듈이 등록되어 있지 않습니다. 파일 접근 승인 창이 뜨면 「모두 허용」을 누르세요.")
            except Exception:
                pass
        try:
            self.com.XHwpWindows.Item(0).Visible = bool(self.visible)
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        try:
            self.com.Clear(1)   # 1 = 저장하지 않고 버림(묻는 창 없음)
        except Exception:
            pass
        try:
            self.com.Quit()
        except Exception:
            try:
                if self._py is not None:
                    self._py.quit()
            except Exception:
                pass
        return False

    def open(self, path: Path, fmt: str = ""):
        path = Path(path).resolve()
        if not path.is_file():
            raise HangulError("파일이 없습니다: %s" % path)
        ok = self.com.Open(str(path), fmt, "forceopen:true")
        if not ok:
            raise HangulError("한글이 파일을 열지 못했습니다: %s\n(암호가 걸렸거나, 배포용 문서이거나, 보안 승인 창에서 거부했을 수 있습니다)" % path)

    def save_as(self, path: Path, fmt: str):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        ok = self.com.SaveAs(str(path), fmt, "")
        for _ in range(50):   # 큰 문서는 파일이 늦게 생길 수 있다
            if path.exists() and path.stat().st_size > 0:
                break
            time.sleep(0.2)
        if not ok or not path.exists():
            raise HangulError("한글이 %s 형식으로 저장하지 못했습니다: %s" % (fmt, path))
        return path

    def page_count(self):
        try:
            return int(self.com.PageCount)
        except Exception:
            return None


# --------------------------------------------------------------------
def cmd_to_hwpx(src, dst):
    src, dst = Path(src), Path(dst)
    with Hangul() as h:
        h.open(src)
        h.save_as(dst, "HWPX")
    if not zipfile.is_zipfile(dst):
        raise HangulError("저장한 파일이 hwpx(zip)가 아닙니다: %s" % dst)
    print("hwpx 로 저장: %s" % dst.resolve())
    print("다음: python inspect_form.py \"%s\"" % dst)


def cmd_to_pdf(src, dst):
    src, dst = Path(src), Path(dst)
    with Hangul() as h:
        h.open(src)
        n = h.page_count()
        h.save_as(dst, "PDF")
    print("PDF 로 저장: %s%s" % (dst.resolve(), "  (%d쪽)" % n if n else ""))
    return n


def cmd_pages(src, outdir, dpi=110):
    try:
        import fitz  # type: ignore  # pymupdf
    except ImportError:
        raise HangulError("pages 를 쓰려면 먼저  pip install pymupdf  를 실행하세요.")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="hwp_pages_"))
    try:
        pdf = tmp / "pages.pdf"
        cmd_to_pdf(src, pdf)
        doc = fitz.open(str(pdf))
        for old in outdir.glob("page-*.png"):   # 지난번 쪽 그림이 섞이지 않게
            old.unlink()
        paths = []
        for i, page in enumerate(doc):
            try:
                pix = page.get_pixmap(dpi=dpi)
            except TypeError:  # 옛 pymupdf
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            p = outdir / ("page-%d.png" % (i + 1))
            pix.save(str(p))
            paths.append(p)
        doc.close()
        shutil.copy(pdf, outdir / (Path(src).stem + ".pdf"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("쪽 그림 %d장: %s" % (len(paths), outdir.resolve()))
    for p in paths:
        print("  " + str(p.resolve()))


def cmd_open(src):
    src = Path(src).resolve()
    if not src.is_file():
        raise HangulError("파일이 없습니다: %s" % src)
    try:
        os.startfile(str(src))  # 기본 연결 프로그램(한글)으로 연다
        print("한글로 열었습니다: %s" % src)
        return
    except OSError as e:
        print("[알림] 기본 프로그램으로 열지 못해 자동화로 엽니다: %s" % e)
    h = Hangul(visible=True).__enter__()   # 사람이 쓰도록 한글을 끄지 않는다
    h.open(src)
    print("한글로 열었습니다: %s" % src)


def main(argv=None):
    _console()
    ap = argparse.ArgumentParser(description="한글(한컴오피스) 자동화: hwp→hwpx, PDF, 쪽 그림, 열기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("to-hwpx", help="hwp → hwpx")
    p.add_argument("src"); p.add_argument("dst")
    p = sub.add_parser("to-pdf", help="hwp/hwpx → PDF (한글 조판 그대로)")
    p.add_argument("src"); p.add_argument("dst")
    p = sub.add_parser("pages", help="PDF 로 저장한 뒤 쪽마다 PNG")
    p.add_argument("src"); p.add_argument("outdir"); p.add_argument("--dpi", type=int, default=110)
    p = sub.add_parser("open", help="한글로 열기")
    p.add_argument("src")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "to-hwpx":
            cmd_to_hwpx(a.src, a.dst)
        elif a.cmd == "to-pdf":
            cmd_to_pdf(a.src, a.dst)
        elif a.cmd == "pages":
            cmd_pages(a.src, a.outdir, a.dpi)
        elif a.cmd == "open":
            cmd_open(a.src)
    except HangulError as e:
        print("[오류] %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
