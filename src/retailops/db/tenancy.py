"""Cách ly theo shop ở tầng kết nối.

Chỉ có ĐÚNG MỘT đường hợp lệ để chạm vào DB: qua shop_scope().
Không có cửa sau, không có "chỉ lần này thôi".

Ba lớp phòng thủ, tính từ dưới lên:
  1. RLS trong Postgres  <- lớp THẬT. Máy ép, người không phá được.
  2. shop_scope()        <- làm cho việc dùng đúng dễ hơn dùng sai.
  3. Repository          <- không lộ ra chỗ nào nhận SQL thô.

Lớp 2 và 3 chỉ để LỖI NỔ SỚM và dễ đọc. Bỏ chúng đi thì hệ thống vẫn an
toàn (nhờ lớp 1), chỉ là khó debug hơn. Bỏ lớp 1 thì hệ thống thủng, dù
lớp 2 và 3 viết đẹp đến đâu.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg

from ..contract.models import ShopId


class TenancyError(RuntimeError):
    """Vi phạm cách ly. Luôn là BUG, không bao giờ là lỗi người dùng."""


class ShopScope:
    """Một giao dịch đã khoá vào đúng một shop.

    Không tự tạo trực tiếp — dùng shop_scope(). Constructor là private theo
    quy ước vì tạo tay sẽ bỏ qua bước SET LOCAL, và lúc đó RLS chặn sạch
    (fail-closed) nhưng lỗi báo ra sẽ là "không tìm thấy dữ liệu" — cực kỳ
    khó lần ra nguyên nhân.
    """

    def __init__(self, conn: psycopg.Connection, shop_id: ShopId) -> None:
        self._conn = conn
        self._shop_id = shop_id

    @property
    def shop_id(self) -> ShopId:
        return self._shop_id

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple]:
        """Chạy SELECT trong phạm vi shop này.

        KHÔNG cần và KHÔNG NÊN viết `WHERE shop_id = ...` trong sql —
        RLS đã tự thêm. Viết thêm cũng không sai, chỉ thừa.

        Đây là điểm đáng chú ý nhất của thiết kế: câu SQL trông như thể
        DB chỉ có dữ liệu của một shop. Người viết truy vấn KHÔNG PHẢI NHỚ
        gì về đa khách hàng cả — và cái gì không phải nhớ thì không quên được.
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


@contextmanager
def shop_scope(conn: psycopg.Connection, shop_id: ShopId) -> Iterator[ShopScope]:
    """Mở một giao dịch khoá vào shop_id. Ra khỏi block là hết hiệu lực.

    HAI CHI TIẾT KHÔNG ĐƯỢC ĐỔI:

    1. set_config(..., is_local=True) — tương đương SET LOCAL, phạm vi
       GIAO DỊCH.

       Dùng SET thường (phạm vi PHIÊN) là lỗi kinh điển giết hệ thống
       multi-tenant: production có connection pool, kết nối được mượn đi
       mượn lại. Request shop A đặt scope, trả kết nối về pool, request
       shop B mượn đúng kết nối đó -> RLS VẪN ĐANG KHOÁ Ở SHOP A.
       Shop B đọc dữ liệu shop A.

       Máy dev không bao giờ bắt được lỗi này: một kết nối, một shop, chạy
       nghìn lần vẫn xanh. Nó chỉ nổ ở production, dưới tải, và log không
       chỉ ra nguyên nhân.

    2. Truyền shop_id qua THAM SỐ, không nối chuỗi.

       `SET LOCAL app.shop_id = '{shop_id}'` là SQL injection. shop_id đến
       từ subdomain, tức là từ người dùng. Đặt được shop_id thành chuỗi
       tuỳ ý là đặt được RLS scope thành shop bất kỳ — nghĩa là đọc được
       dữ liệu shop bất kỳ.

       psycopg không cho tham số hoá `SET`, nên dùng hàm set_config().
    """
    if not shop_id:
        raise TenancyError("shop_id rỗng — không mở scope được")

    with conn.transaction():
        with conn.cursor() as cur:
            # tham số $2 = giá trị, $3 = is_local (True = SET LOCAL)
            cur.execute("SELECT set_config('app.shop_id', %s, true)", (shop_id,))
        yield ShopScope(conn, shop_id)


def current_scope(conn: psycopg.Connection) -> str | None:
    """Scope đang có hiệu lực. Chỉ dùng để debug và để TEST kiểm chứng."""
    with conn.cursor() as cur:
        cur.execute("SELECT current_setting('app.shop_id', true)")
        row = cur.fetchone()
    # Chuỗi rỗng nghĩa là đã từng đặt rồi bị reset -> coi như chưa đặt.
    return (row[0] or None) if row else None
