"""Bộ test CỐ TÌNH TẤN CÔNG cách ly giữa các shop.

Sổ Quyết Định Q5.4: "Không đo được bằng cách dùng thử — phải viết test
cố tình tấn công." Rủi ro R1 là rủi ro DUY NHẤT có thể chấm dứt công ty.

    🔴 KHÔNG NHẬN KHÁCH THỨ HAI TRƯỚC KHI FILE NÀY XANH TOÀN BỘ.

Mỗi test dưới đây là một cách rò dữ liệu ĐÃ TỪNG XẢY RA ở hệ thống thật.
Không có cái nào là giả định lý thuyết.
"""

from __future__ import annotations

import psycopg
import pytest

from retailops.db import ProductRepository, TenancyError, current_scope, shop_scope

# ══════════════════════════════════════════════════════════════
# NHÓM A — Cấu hình. Sai ở đây thì mọi test khác vô nghĩa.
# ══════════════════════════════════════════════════════════════


def test_vai_tro_ung_dung_khong_phai_superuser(conn):
    """Superuser ĐI XUYÊN RLS. Chạy app bằng superuser = mọi policy là trang trí.

    Đây là lỗi cấu hình phổ biến nhất khi làm RLS: làm đúng hết rồi vô hiệu
    hoá toàn bộ bằng một dòng chuỗi kết nối.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        is_super, bypass = cur.fetchone()
    assert not is_super, "ứng dụng đang chạy bằng superuser — RLS bị vô hiệu"
    assert not bypass, "vai trò có BYPASSRLS — RLS bị vô hiệu"


def test_rls_dang_bat_va_forced(conn):
    """FORCE cũng phải bật, không chỉ ENABLE.

    Thiếu FORCE thì CHỦ BẢNG đi xuyên policy. Lúc dev người ta hay kết nối
    bằng chính chủ bảng -> test xanh, production thủng.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relname IN ('products','variants')"
        )
        for name, enabled, forced in cur.fetchall():
            assert enabled, f"{name}: chưa ENABLE ROW LEVEL SECURITY"
            assert forced, f"{name}: chưa FORCE ROW LEVEL SECURITY"


# ══════════════════════════════════════════════════════════════
# NHÓM B — Fail closed: hỏng phải hỏng về phía AN TOÀN
# ══════════════════════════════════════════════════════════════


def test_khong_dat_scope_thi_KHONG_THAY_GI(conn):
    """Quên đặt scope -> 0 dòng, KHÔNG PHẢI tất cả.

    Đây là quyết định thiết kế quan trọng nhất của cả tầng. Hướng hỏng phải
    luôn là hướng an toàn. Hệ thống hỏng theo kiểu "không thấy gì" thì có
    người báo trong 5 phút. Hỏng theo kiểu "thấy hết" thì không ai báo, và
    anh biết tin từ báo chí.
    """
    assert current_scope(conn) is None
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM products")
        assert cur.fetchone()[0] == 0


def test_scope_rong_bi_tu_choi_ngay(conn):
    with pytest.raises(TenancyError):
        with shop_scope(conn, ""):
            pass


# ══════════════════════════════════════════════════════════════
# NHÓM C — Đọc chéo shop  (Q5.4 gạch 3)
# ══════════════════════════════════════════════════════════════


def test_shop_A_chi_thay_du_lieu_cua_minh(conn):
    with shop_scope(conn, "shop-a") as scope:
        names = {r[0] for r in scope.query("SELECT name FROM products")}
    assert names == {"Giày thể thao bé trai", "Dép quai hậu bé gái"}
    assert not any("shop B" in n for n in names)


def test_trung_ma_san_pham_khong_lan_sang_nhau(conn):
    """Cả hai shop đều có mã 'SP001' — mỗi bên phải thấy đúng của mình.

    Nếu khoá chính chỉ là (id) thay vì (shop_id, id), shop thứ hai nhập
    'SP001' sẽ đâm vào shop thứ nhất. Rò dữ liệu mà không ai gọi nó là rò.
    """
    with shop_scope(conn, "shop-a") as s:
        assert ProductRepository(s).get("SP001").name == "Giày thể thao bé trai"
    with shop_scope(conn, "shop-b") as s:
        assert ProductRepository(s).get("SP001").name == "Sản phẩm MẬT của shop B"


def test_khong_lay_duoc_san_pham_shop_khac_du_biet_dung_ma(conn):
    """Biết chính xác mã 'BIMAT' của shop B cũng không lấy được."""
    with shop_scope(conn, "shop-a") as s:
        assert ProductRepository(s).get("BIMAT") is None


def test_ham_tong_hop_cung_bi_chan(conn):
    """COUNT/SUM cũng phải bị RLS lọc.

    Nhiều người tưởng RLS chỉ lọc dòng TRẢ VỀ nên hàm tổng hợp vẫn đếm cả
    bảng. Nếu vậy, shop A đoán được shop B có bao nhiêu hàng, doanh thu
    bao nhiêu. Rò con số cũng là rò.
    """
    with shop_scope(conn, "shop-a") as s:
        assert ProductRepository(s).count() == 2  # không phải 4
    with shop_scope(conn, "shop-b") as s:
        assert ProductRepository(s).count() == 2


def test_variant_khong_lan_sang_shop_khac(conn):
    with shop_scope(conn, "shop-a") as s:
        p = ProductRepository(s).get("SP001")
        assert [v.id for v in p.variants] == ["SP001-26"]


# ══════════════════════════════════════════════════════════════
# NHÓM D — Ghi chéo shop. Rò MỘT CHIỀU vẫn là rò.
# ══════════════════════════════════════════════════════════════


def test_khong_UPDATE_duoc_dong_cua_shop_khac(conn):
    with shop_scope(conn, "shop-a") as s:
        n = s.execute("UPDATE products SET price = 1 WHERE id = 'BIMAT'")
    assert n == 0
    with shop_scope(conn, "shop-b") as s:
        assert ProductRepository(s).get("BIMAT").price == 888000


def test_khong_DELETE_duoc_dong_cua_shop_khac(conn):
    with shop_scope(conn, "shop-a") as s:
        assert s.execute("DELETE FROM products WHERE id = 'BIMAT'") == 0
    with shop_scope(conn, "shop-b") as s:
        assert ProductRepository(s).get("BIMAT") is not None


def test_khong_INSERT_duoc_dong_mang_shop_id_cua_nguoi_khac(conn):
    """WITH CHECK chặn. Thiếu nó thì shop A không ĐỌC được dữ liệu shop B
    nhưng vẫn GHI ĐÈ được vào — tệ hơn đọc trộm."""
    with pytest.raises(psycopg.errors.Error):
        with shop_scope(conn, "shop-a") as s:
            s.execute(
                "INSERT INTO products (shop_id, id, name) VALUES ('shop-b','HACK','độc hại')"
            )


# ══════════════════════════════════════════════════════════════
# NHÓM E — Đi vòng qua repository  (Q5.4 gạch 2)
# ══════════════════════════════════════════════════════════════


def test_SQL_THO_khong_co_WHERE_van_bi_chan(conn):
    """Dev mệt, mở psycopg gọi thẳng, quên WHERE shop_id.

    Đây là ca mà mọi quy ước ở tầng Python đều thất bại. RLS là lớp duy
    nhất còn đứng. Nếu test này đỏ thì toàn bộ kiến trúc chỉ là lời hứa.
    """
    with shop_scope(conn, "shop-a"):
        with conn.cursor() as cur:
            cur.execute("SELECT shop_id FROM products")  # cố tình không lọc
            assert {r[0] for r in cur.fetchall()} == {"shop-a"}


def test_JOIN_khong_keo_duoc_du_lieu_shop_khac(conn):
    with shop_scope(conn, "shop-a"):
        with conn.cursor() as cur:
            cur.execute("SELECT p.shop_id, v.shop_id FROM products p JOIN variants v ON true")
            for a, b in cur.fetchall():
                assert a == b == "shop-a"


def test_subquery_khong_ro_du_lieu_shop_khac(conn):
    with shop_scope(conn, "shop-a"):
        with conn.cursor() as cur:
            cur.execute("SELECT (SELECT count(*) FROM products WHERE shop_id = 'shop-b')")
            assert cur.fetchone()[0] == 0


# ══════════════════════════════════════════════════════════════
# NHÓM F — Rò rỉ qua CONNECTION POOL. Lỗi giết nhiều hệ thống thật nhất.
# ══════════════════════════════════════════════════════════════


def test_scope_KHONG_song_sot_qua_giao_dich(conn):
    """Bằng chứng SET LOCAL chứ không phải SET.

    Production dùng pool: kết nối được mượn đi mượn lại. Nếu scope sống
    qua giao dịch thì request shop B mượn phải kết nối cũ của shop A sẽ
    đọc dữ liệu shop A.

    Máy dev KHÔNG BAO GIỜ bắt được lỗi này — một kết nối, một shop, chạy
    nghìn lần vẫn xanh. Nó chỉ nổ ở production, dưới tải.
    """
    with shop_scope(conn, "shop-a") as s:
        assert s.query("SELECT count(*) FROM products")[0][0] == 2
    # ra khỏi block = hết giao dịch = scope phải bay
    assert current_scope(conn) is None
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM products")
        assert cur.fetchone()[0] == 0, "SCOPE RÒ QUA GIAO DỊCH — đang dùng SET thay vì SET LOCAL"


def test_hai_scope_lien_tiep_khong_dinh_nhau(conn):
    with shop_scope(conn, "shop-a") as s:
        assert ProductRepository(s).get("SP001").name == "Giày thể thao bé trai"
    with shop_scope(conn, "shop-b") as s:
        assert ProductRepository(s).get("SP001").name == "Sản phẩm MẬT của shop B"
    with shop_scope(conn, "shop-a") as s:
        assert ProductRepository(s).get("BIMAT") is None


def test_scope_bay_ca_khi_giao_dich_hong(conn):
    """Giao dịch nổ giữa chừng cũng không được để lại scope trên kết nối."""
    with pytest.raises(psycopg.errors.Error):
        with shop_scope(conn, "shop-a") as s:
            s.execute("SELECT * FROM bang_khong_ton_tai")
    conn.rollback()
    assert current_scope(conn) is None


# ══════════════════════════════════════════════════════════════
# NHÓM G — shop_id đến từ NGƯỜI DÙNG (subdomain). Coi là thù địch.
# ══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("doc_hai", [
    "shop-a' OR '1'='1",
    "shop-a'; DROP TABLE products; --",
    "' OR 1=1 --",
    "shop-a\x00shop-b",
])
def test_shop_id_doc_hai_khong_pha_duoc_scope(conn, doc_hai):
    """shop_id đến từ subdomain -> từ người dùng.

    Nếu nối chuỗi vào `SET LOCAL app.shop_id = '...'` thì đặt được scope
    thành shop bất kỳ = đọc được dữ liệu shop bất kỳ. set_config() tham số
    hoá biến chúng thành chuỗi vô hại, khớp 0 shop.
    """
    try:
        with shop_scope(conn, doc_hai) as s:
            assert s.query("SELECT count(*) FROM products")[0][0] == 0
    except psycopg.errors.Error:
        conn.rollback()  # từ chối thẳng cũng là kết quả chấp nhận được
    with conn.cursor() as cur:  # bảng phải còn nguyên
        cur.execute("SELECT to_regclass('public.products')")
        assert cur.fetchone()[0] is not None


# ══════════════════════════════════════════════════════════════
# NHÓM H — Bất biến hợp đồng phải sống sót qua vòng ghi–đọc DB
# ══════════════════════════════════════════════════════════════


def test_bien_the_mu_ton_thi_tong_ton_van_la_None_sau_khi_qua_DB(conn):
    """Bất biến số 4 không được mất khi dữ liệu đi qua Postgres.

    Bất biến chỉ ép ở tầng Python sẽ bị phá bởi import, sửa tay, migration.
    Phải ép ở CẢ chỗ ghi lẫn chỗ đọc.
    """
    with shop_scope(conn, "shop-a") as s:
        p = ProductRepository(s).get("SP002")
    assert any(v.stock is None for v in p.variants)
    assert p.total_stock is None


def test_DB_tu_choi_ton_kho_am(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        with shop_scope(conn, "shop-a") as s:
            s.execute("UPDATE products SET total_stock = -5 WHERE id = 'SP001'")


# ══════════════════════════════════════════════════════════════
# NHÓM I — CHƯA LÀM ĐƯỢC. Để lộ ra, không giấu đi.
# ══════════════════════════════════════════════════════════════
# Q5.4 còn 3 gạch cần tầng chưa dựng. Viết thành test bỏ qua có LÝ DO
# thay vì gạch đầu dòng trong tài liệu — vì test bỏ qua thì mỗi lần chạy
# pytest đều nhắc, còn gạch trong tài liệu thì sẽ quên.


@pytest.mark.skip(reason="cần tầng auth/API (chưa dựng) — Q5.4 gạch 1")
def test_token_shop_A_goi_subdomain_shop_B_phai_403():
    ...


@pytest.mark.skip(reason="cần lõi agent T4 (chưa dựng) — Q5.4 gạch 4")
def test_model_shop_A_nhac_id_san_pham_shop_B_phai_bi_gate_chan():
    ...


@pytest.mark.skip(reason="cần tầng session (chưa dựng) — Q5.4 gạch 5")
def test_session_id_shop_A_dung_cho_shop_B_phai_401():
    ...


# ══════════════════════════════════════════════════════════════
# NHÓM J — Chặn lỗ hổng SINH RA KHI HỆ THỐNG LỚN LÊN
# ══════════════════════════════════════════════════════════════
# Mọi test phía trên chỉ kiểm 2 bảng đang có. Bảng thứ 12 tạo 4 tháng nữa,
# lúc vội, quên bật RLS -> không test nào kêu, vì không test nào biết nó
# tồn tại.
#
# Test dưới đây QUÉT TOÀN BỘ DATABASE. Bảng mới buộc phải khai báo rõ nó
# thuộc nhóm nào. Không khai = CI đỏ.
#
# Đây là kiểu test đáng giá nhất trong hệ thống sống lâu: nó không kiểm
# code đã viết, nó kiểm code SẼ ĐƯỢC VIẾT.

# Bảng cấp nền tảng — cố ý KHÔNG có RLS, và phải giải thích vì sao.
# Thêm tên vào đây là một quyết định có ý thức, không phải việc làm cho xong.
BANG_KHONG_CAN_RLS = {
    "shops": "sổ đăng ký khách. Không chứa dữ liệu kinh doanh của shop nào. "
             "Chỉ tầng nền tảng đọc, không lộ ra API của shop.",
}


def test_MOI_bang_du_lieu_shop_deu_phai_bat_RLS(conn):
    """Bảng mới quên bật RLS = thủng. Test này bắt trước khi có khách."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r'
             ORDER BY c.relname
        """)
        tables = cur.fetchall()

    assert tables, "không tìm thấy bảng nào — fixture hỏng"

    for name, enabled, forced in tables:
        if name in BANG_KHONG_CAN_RLS:
            continue
        assert enabled and forced, (
            f"\n  Bảng '{name}' chưa bật RLS đầy đủ "
            f"(ENABLE={enabled}, FORCE={forced}).\n"
            f"  Thêm vào schema.sql:\n"
            f"      ALTER TABLE {name} ENABLE ROW LEVEL SECURITY;\n"
            f"      ALTER TABLE {name} FORCE ROW LEVEL SECURITY;\n"
            f"      CREATE POLICY tenant_isolation ON {name}\n"
            f"          USING      (shop_id = current_setting('app.shop_id', true))\n"
            f"          WITH CHECK (shop_id = current_setting('app.shop_id', true));\n"
            f"  Hoặc nếu đây là bảng cấp nền tảng, thêm vào BANG_KHONG_CAN_RLS\n"
            f"  KÈM LÝ DO."
        )


def test_MOI_bang_du_lieu_shop_deu_phai_co_cot_shop_id(conn):
    """Không có cột shop_id thì policy RLS không viết nổi.

    Bắt ở tầng schema thay vì đợi tới lúc viết policy: lỗi hiện ra sớm hơn
    và thông báo dễ hiểu hơn nhiều.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r'
               AND NOT EXISTS (
                   SELECT 1 FROM pg_attribute a
                    WHERE a.attrelid = c.oid AND a.attname = 'shop_id' AND a.attnum > 0
               )
        """)
        thieu = {r[0] for r in cur.fetchall()} - set(BANG_KHONG_CAN_RLS)
    assert not thieu, f"bảng thiếu cột shop_id: {sorted(thieu)}"


def test_MOI_bang_du_lieu_shop_deu_phai_co_policy(conn):
    """Bật RLS mà quên tạo policy -> fail-closed: KHÔNG AI đọc được gì.

    Hệ thống không rò dữ liệu, nhưng ngừng hoạt động. Bắt được ở CI thì
    đỡ hơn bắt được lúc khách gọi điện.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
               AND NOT EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid)
        """)
        assert not [r[0] for r in cur.fetchall()], "bảng bật RLS nhưng không có policy"
