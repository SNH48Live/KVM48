import os
import re
import time
import urllib.parse
from typing import Optional


__all__ = [
    "extension_from_url",
    "sanitize_filename",
    "sanitize_filepath",
    "read_keypress_with_timeout",
]


def extension_from_url(url: str, *, dot: bool = False) -> str:
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
    return ext if dot else ext[1:]


def collapse_filename_spaces(unsanitized: str) -> str:
    # Collapse consecutive spaces.
    result = re.sub(r" +", " ", unsanitized)
    # Remove space before the file extension.
    result = re.sub(r" (?=\.[^.]+$)", "", result)
    return result


def sanitize_filename(unsanitized: str, convert_non_bmp_chars="keep") -> str:
    # Strip control characters (0x00-0x1F, 0x7F), and use homoglyphs
    # (Halfwidth and Fullwidth Forms block, U+FF00 - U+FFEF) for
    # characters illegal in exFAT/NTFS:
    #
    # " => U+FF02 FULLWIDTH QUOTATION MARK (＂)
    # * => U+FF0A FULLWIDTH ASTERISK (＊)
    # / => U+FF0F FULLWIDTH SOLIDUS (／)
    # : => U+FF1A FULLWIDTH COLON (：)
    # < => U+FF1C FULLWIDTH LESS-THAN SIGN (＜)
    # > => U+FF1E FULLWIDTH GREATER-THAN SIGN (＞)
    # ? => U+FF1F FULLWIDTH QUESTION MARK (？)
    # \ => U+FF3C FULLWIDTH REVERSE SOLIDUS (＼)
    # | => U+FF5C FULLWIDTH VERTICAL LINE (｜)
    #
    # Also replace whitespace characters with space.
    #
    # The convert_non_bmp_chars option determines how non-BMP
    # characters (not in the Basic Multilingual Plane, i.e., code
    # points beyond U+FFFF) are treated. Conversion is necessary is
    # necessary for certain legacy filesystems with only UCS-2 support,
    # e.g., FAT32.
    #
    # The value of this option can be one of 'keep', 'strip',
    # 'replace', 'question_mark', or any single BMP character (U+0001
    # to U+FFFF). 'keep' keeps the characters intact (default
    # behavior); 'strip' strips all non-BMP characters; 'replace'
    # replaces all non-BMP characters with U+FFFD (REPLACEMENT
    # CHARACTER �); 'question_mark' replaces all non-BMP characters
    # with U+003F (QUESTION MARK ?); otherwise, a single BMP character
    # specifies the replacement character for non-BMP characters
    # directly.
    result = re.sub(r"[\x00-\x1f\x7f]+", "", unsanitized).translate(
        str.maketrans(
            '"*/:<>?\\|\t\n\r\f\v',
            "\uFF02\uFF0A\uFF0F\uFF1A\uFF1C\uFF1E\uFF1F\uFF3C\uFF5C     ",
        )
    )
    if convert_non_bmp_chars == "keep":
        return collapse_filename_spaces(result)
    else:
        if convert_non_bmp_chars == "strip":
            repl = ""
        elif convert_non_bmp_chars == "replace":
            repl = "\uFFFD"
        elif convert_non_bmp_chars == "question_mark":
            repl = "?"
        elif len(convert_non_bmp_chars) == 1:
            repl = convert_non_bmp_chars
            codepoint = ord(repl)
            if codepoint <= 0x1F or codepoint == 0x7F or codepoint > 0xFFFF:
                raise ValueError("invalid replacement character %s" % repr(repl))
        else:
            raise ValueError(
                "unrecognized convert_non_bmp_chars %s" % repr(convert_non_bmp_chars)
            )
        result = "".join(ch if ord(ch) <= 0xFFFF else repl for ch in result)
        return collapse_filename_spaces(result)


def sanitize_filepath(unsanitized: str, convert_non_bmp_chars="keep") -> str:
    return os.sep.join(
        sanitize_filename(seg, convert_non_bmp_chars=convert_non_bmp_chars)
        for seg in unsanitized.split(os.sep)
    )


if os.name == "posix":
    import select
    import sys
    import termios
    import tty

    def read_keypress_with_timeout(timeout: float) -> Optional[str]:
        end_time = time.time() + timeout
        stdin_fileno = sys.stdin.fileno()
        saved_tcattr = termios.tcgetattr(stdin_fileno)
        try:
            tty.setcbreak(stdin_fileno)
            while time.time() <= end_time:
                if select.select((sys.stdin,), (), (), 0.1)[0]:
                    return sys.stdin.read(1)
        finally:
            termios.tcsetattr(stdin_fileno, termios.TCSAFLUSH, saved_tcattr)


elif os.name == "nt":
    try:
        import msvcrt

        def read_keypress_with_timeout(timeout: float) -> Optional[str]:
            end_time = time.time() + timeout
            while time.time() <= end_time:
                if msvcrt.kbhit():
                    return msvcrt.getwch()

    except ImportError:

        def read_keypress_with_timeout(timeout: float) -> None:
            time.sleep(timeout)


else:

    def read_keypress_with_timeout(timeout: float) -> None:
        time.sleep(timeout)
