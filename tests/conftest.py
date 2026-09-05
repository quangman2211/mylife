"""Hạ tầng test cho phần cách ly tenant.

Điểm mấu chốt: test KẾT NỐI BẰNG VAI TRÒ CỦA ỨNG DỤNG, không phải superuser.

Nếu test dùng superuser thì Postgres cho đi xuyên RLS, mọi test dưới đây
sẽ XANH trong khi production thủng. Đó là kiểu lỗi tệ nhất — bộ test nói
"an toàn" trong khi thực tế không.
"""

from __future__ import annotations

import os

import pytest

psycopg = pytest.importorskip("psycopg")

# Không hardcode DSN: CI, máy dev và container mỗi nơi một khác.
# Hardcode thì test chỉ chạy được trên đúng máy người viết ra nó — mà test
# không chạy tự động thì không bảo vệ được gì.
PG_HOST = os.environ.get("PGHOST", "/tmp")
PG_PORT = os.environ.get("PGPORT", "5433")
PG_ADMIN_USER = os.environ.get("PGUSER", "postgres")
PG_ADMIN_PW = os.environ.get("PGPASSWORD", "")
APP_ROLE = "retailops_app"
APP_PW = "test"
TEST_DB = "retailops_test"


def _dsn(user: str, password: str, dbname: str) -> str:
    parts = [f"host={PG_HOST}", f"port={PG_PORT}", f"user={user}", f"dbname={dbname}"]
    if password:
        parts.append(f"password={password}")
    return " ".join(parts)


def _admin(dbname: str = "postgres"):
    return psycopg.connect(_dsn(PG_ADMIN_USER, PG_ADMIN_PW, dbname), autocommit=True)


@pytest.fixture(scope="session")
def pg_ready() -> str:
    """Dựng DB test + vai trò ứng dụng. Trả về DSN của vai trò ứng dụng."""
    try:
        admin = _admin()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"không có Postgres: {exc}")

    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {TEST_DB}")
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_ROLE,))
        if not cur.fetchone():
            # NOSUPERUSER tường minh. Superuser đi xuyên RLS -> mọi policy
            # thành trang trí. Đây là lỗi cấu hình phổ biến nhất khi làm RLS.
            cur.execute(f"CREATE ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{APP_PW}'")
    admin.close()

    schema = open("src/retailops/db/schema.sql", encoding="utf-8").read()
    admin_db = _admin(TEST_DB)
    with admin_db.cursor() as cur:
        cur.execute(schema)
        # Vai trò ứng dụng CHỈ có quyền DML. Không phải chủ bảng
        # (chủ bảng là postgres) -> RLS áp bình thường.
        cur.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
        cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    admin_db.close()

    return _dsn(APP_ROLE, APP_PW, TEST_DB)


@pytest.fixture
def seeded(pg_ready):
    """Xoá sạch rồi nạp dữ liệu 2 shop. Seed bằng superuser (đi xuyên RLS).

    Vì sao seed bằng superuser: để dựng được tình huống "DB có dữ liệu của
    shop khác". Không có dữ liệu shop B thì không chứng minh được shop A
    KHÔNG đọc được nó — test sẽ xanh vì bảng rỗng, chứ không phải vì RLS.
    """
    admin = _admin(TEST_DB)
    with admin.cursor() as cur:
        cur.execute("TRUNCATE variants, products, shops CASCADE")
        cur.execute("INSERT INTO shops (id, name) VALUES ('shop-a','Khải Kids'), ('shop-b','Shop Đối Thủ')")
        cur.execute("""
            INSERT INTO products (shop_id, id, name, price, total_stock) VALUES
              ('shop-a','SP001','Giày thể thao bé trai', 285000, 15),
              ('shop-a','SP002','Dép quai hậu bé gái',   155000, NULL),
              ('shop-b','SP001','Sản phẩm MẬT của shop B', 999000, 7),
              ('shop-b','BIMAT','Hàng độc quyền shop B',  888000, 3)
        """)
        cur.execute("""
            INSERT INTO variants (shop_id, id, product_id, size, color, price, stock) VALUES
              ('shop-a','SP001-26','SP001','26','Xanh',285000,4),
              ('shop-a','SP002-27','SP002','27','Hồng',155000,NULL),
              ('shop-b','BIMAT-1','BIMAT','30','Đen',888000,3)
        """)
    admin.close()
    return pg_ready


@pytest.fixture
def conn(seeded):
    """Kết nối bằng VAI TRÒ ỨNG DỤNG — không phải superuser."""
    c = psycopg.connect(seeded)
    yield c
    c.close()
