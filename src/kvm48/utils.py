import os
import re
import urllib.parse


def extension_from_url(url: str, *, dot: bool = False) -> str:
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
    return ext if dot else ext[1:]


def sanitize_filename(unsanitized: str) -> str:
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
    # Also replace whitespace characters with the space
    return re.sub(r"[\x00-\x1f\x7f]+", "", unsanitized).translate(
        str.maketrans(
            '"*/:<>?\\|\t\n\r\f\v',
            "\uFF02\uFF0A\uFF0F\uFF1A\uFF1C\uFF1E\uFF1F\uFF3C\uFF5C     ",
        )
    )


def sanitize_filepath(unsanitized: str) -> str:
    return os.sep.join(sanitize_filename(seg) for seg in unsanitized.split(os.sep))
