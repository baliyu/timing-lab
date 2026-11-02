import random
import re
from pathlib import Path

import pytest

from timing_lab import hostlib

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def fns():
    return hostlib.load()


def test_all_three_agree_with_plain_equality_on_random_strings(fns):
    rnd = random.Random(1)
    for _ in range(3000):
        n = rnd.randint(0, 40)
        a = bytes(rnd.randrange(256) for _ in range(n))
        b = a if rnd.random() < 0.4 else bytes(rnd.randrange(256) for _ in range(n))
        for name, f in fns.items():
            assert f(a, b, n) == (1 if a == b else 0), name


@pytest.mark.parametrize("n", [1, 2, 4, 16, 32, 255])
def test_a_single_changed_byte_at_every_position_is_found_by_all_three(fns, n):
    a = bytes(range(n)) if n < 256 else bytes(255)
    for pos in range(n):
        b = bytearray(a)
        b[pos] ^= 0x80
        for name, f in fns.items():
            assert f(a, bytes(b), n) == 0, (name, n, pos)
        assert all(f(a, a, n) == 1 for f in fns.values())


def test_a_length_of_zero_means_equal_for_all_three(fns):
    assert all(f(b"", b"", 0) == 1 for f in fns.values())


def test_only_the_first_n_bytes_are_compared(fns):
    a, b = b"ABCDxxxx", b"ABCDyyyy"
    assert all(f(a, b, 4) == 1 for f in fns.values())
    assert all(f(a, b, 5) == 0 for f in fns.values())


def test_the_constant_time_function_has_the_three_body_lines_of_the_secure_link_unchanged():
    src = (ROOT / "c" / "compare.c").read_text(encoding="utf-8")
    body = ("  uint8_t diff = 0, i;\n"
            "  for (i = 0; i < n; i++) diff |= (uint8_t)(a[i] ^ b[i]);\n"
            "  return diff == 0;\n")
    assert re.search(r"int cmp_ct\(const uint8_t \*a, const uint8_t \*b, uint8_t n\)\n\{\n" + re.escape(body) + r"\}", src)
