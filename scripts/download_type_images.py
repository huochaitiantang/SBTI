#!/usr/bin/env python3
"""
从 data/types.json 读取所有 personality code，下载
https://sbti.unun.dev/image/{code}.png 到本地目录。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "https://sbti.unun.dev/image"

# 默认路径：本脚本位于 scripts/，数据在上一级 data/
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
DEFAULT_TYPES_PATH = _REPO_ROOT / "data" / "types.json"
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "images"

# Windows 等系统不允许文件名含 \/:*?"<>|
_INVALID_FS = frozenset('\\/:*?"<>|')


def local_png_name(code: str) -> str:
    """与 code 一一对应的本地文件名（去掉路径非法字符）。"""
    safe = "".join("_" if c in _INVALID_FS else c for c in code)
    return f"{safe}.png"


def load_codes(types_path: Path) -> list[str]:
    data = json.loads(types_path.read_text(encoding="utf-8"))
    codes: list[str] = []
    for key in ("standard", "special"):
        for item in data.get(key, []):
            c = item.get("code")
            if isinstance(c, str) and c.strip():
                codes.append(c.strip())
    return codes


def image_url(code: str) -> str:
    # 路径段编码：? ! 等否则会被当作查询串或需转义
    return f"{BASE_URL}/{quote(code, safe='-')}.png"


def download_one(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": "SBTI-type-images/1.0"})
    with urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 SBTI 类型 PNG 图片")
    parser.add_argument(
        "--types-json",
        type=Path,
        default=DEFAULT_TYPES_PATH,
        help=f"types.json 路径（默认: {DEFAULT_TYPES_PATH}）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"保存目录（默认: {DEFAULT_OUT_DIR}）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若目标文件已存在则跳过",
    )
    args = parser.parse_args()

    if not args.types_json.is_file():
        print(f"错误: 找不到 {args.types_json}", file=sys.stderr)
        return 1

    codes = load_codes(args.types_json)
    if not codes:
        print("未找到任何 code。", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    ok, fail = 0, 0
    for code in codes:
        url = image_url(code)
        dest = args.out / local_png_name(code)
        # if args.skip_existing and dest.is_file():
        if dest.is_file():
            print(f"[skip] {dest.name}")
            ok += 1
            continue
        try:
            download_one(url, dest)
            print(f"[ok]   {url} -> {dest}")
            ok += 1
        except HTTPError as e:
            print(f"[fail] {url} HTTP {e.code}", file=sys.stderr)
            fail += 1
        except URLError as e:
            print(f"[fail] {url} {e.reason}", file=sys.stderr)
            fail += 1
        except OSError as e:
            print(f"[fail] {dest} {e}", file=sys.stderr)
            fail += 1

    print(f"完成: 成功 {ok}, 失败 {fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
