-- T2 — Kho chuẩn hoá. Một DB chứa MỌI shop, cách ly bằng Row Level Security.
--
-- Vì sao chung bảng + RLS chứ không phải schema-per-tenant: xem ADR-0002.
--
-- ĐỌC KỸ PHẦN RLS Ở CUỐI FILE. Ba dòng ở đó là thứ duy nhất đứng giữa
-- "một dự án" và "một vụ rò dữ liệu chấm dứt công ty" (rủi ro R1).

-- ============================================================
-- VAI TRÒ
-- ============================================================
-- Ứng dụng KHÔNG chạy bằng superuser và KHÔNG phải chủ bảng.
--
-- Vì sao quan trọng: Postgres cho superuser và chủ bảng ĐI XUYÊN RLS.
-- Chạy app bằng postgres thì mọi policy dưới đây là trang trí.
-- Đây là lỗi phổ biến nhất khi làm RLS — làm đủ mọi thứ rồi vô hiệu hoá
-- toàn bộ bằng đúng một dòng cấu hình kết nối.

-- CREATE ROLE retailops_app LOGIN PASSWORD '...';   -- chạy lúc provision
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO retailops_app;

-- ============================================================
-- BẢNG
-- ============================================================

CREATE TABLE IF NOT EXISTS shops (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    -- shop_id ĐỨNG ĐẦU, cố ý. Ai đọc bảng này cũng phải thấy nó trước tiên.
    -- Blueprint: "shop_id phải có trong mọi bảng từ dòng code đầu tiên."
    shop_id       text NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    id            text NOT NULL,
    name          text NOT NULL,

    -- Tiền: bigint VNĐ, KHÔNG dùng float/real.
    -- numeric cũng được nhưng bigint nhanh hơn và giá VN không có phần lẻ.
    price         bigint,

    -- NULL = KHÔNG BIẾT. 0 = ĐÃ KIỂM, HẾT HÀNG.
    -- Ràng buộc này đi thẳng từ contract/models.py xuống. Cùng một quy tắc,
    -- ép ở CẢ HAI tầng — vì dữ liệu có thể vào DB bằng đường khác (import,
    -- sửa tay, migration) chứ không chỉ qua code Python.
    total_stock   integer,

    description   text,
    synced_at     timestamptz NOT NULL DEFAULT now(),

    -- Khoá chính GỘP shop_id. Hệ quả: hai shop được phép trùng mã "SP001".
    -- Nếu chỉ PRIMARY KEY(id) thì shop thứ hai nhập "SP001" sẽ đâm vào shop
    -- thứ nhất — một dạng rò dữ liệu mà không ai nghĩ là rò dữ liệu.
    PRIMARY KEY (shop_id, id),

    CONSTRAINT stock_khong_am CHECK (total_stock IS NULL OR total_stock >= 0),
    CONSTRAINT gia_khong_am   CHECK (price IS NULL OR price >= 0)
);

CREATE TABLE IF NOT EXISTS variants (
    shop_id     text NOT NULL,
    id          text NOT NULL,
    product_id  text NOT NULL,
    sku         text,
    size        text,
    color       text,
    price       bigint,
    stock       integer,

    PRIMARY KEY (shop_id, id),

    -- Khoá ngoại GỘP shop_id. Không có shop_id trong FK thì biến thể của
    -- shop A có thể trỏ vào sản phẩm của shop B — và Postgres sẽ cho phép.
    FOREIGN KEY (shop_id, product_id) REFERENCES products(shop_id, id) ON DELETE CASCADE,
    CONSTRAINT variant_stock_khong_am CHECK (stock IS NULL OR stock >= 0)
);

-- Index luôn có shop_id ĐỨNG ĐẦU. Mọi truy vấn đều bị RLS thêm điều kiện
-- shop_id vào, nên index không dẫn đầu bằng shop_id sẽ không được dùng.
CREATE INDEX IF NOT EXISTS idx_products_shop_name ON products (shop_id, name);
CREATE INDEX IF NOT EXISTS idx_variants_shop_product ON variants (shop_id, product_id);

-- ============================================================
-- ROW LEVEL SECURITY — lớp phòng thủ THẬT
-- ============================================================
--
-- Cơ chế: ứng dụng đặt app.shop_id ở đầu mỗi giao dịch. Postgres tự thêm
-- điều kiện shop_id = <giá trị đó> vào MỌI câu lệnh trên bảng này —
-- SELECT, UPDATE, DELETE, và cả COUNT/SUM.
--
-- Code quên WHERE shop_id? Không sao, DB vẫn chặn.
-- Dev mở psycopg gọi SQL thẳng? Không sao, DB vẫn chặn.
--
-- ĐÓ là khác biệt giữa "cẩn thận" và "an toàn".

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE variants ENABLE ROW LEVEL SECURITY;

-- FORCE: áp RLS cho CẢ CHỦ BẢNG.
-- Không có dòng này, chủ bảng đi xuyên policy — và lúc dev/test người ta
-- hay kết nối bằng chính chủ bảng, nên test sẽ XANH trong khi production
-- thủng. Kiểu lỗi tệ nhất: test nói an toàn, thực tế không.
ALTER TABLE products FORCE ROW LEVEL SECURITY;
ALTER TABLE variants FORCE ROW LEVEL SECURITY;

-- current_setting(..., true) -> trả NULL khi chưa đặt, thay vì báo lỗi.
--   NULL thì `shop_id = NULL` cho ra NULL, không phải TRUE
--   -> không dòng nào lọt.
--
-- Đây là FAIL-CLOSED: quên đặt scope thì thấy 0 dòng, KHÔNG phải thấy tất cả.
-- Hướng hỏng phải luôn là hướng an toàn.
DROP POLICY IF EXISTS tenant_isolation ON products;
CREATE POLICY tenant_isolation ON products
    USING       (shop_id = current_setting('app.shop_id', true))
    WITH CHECK  (shop_id = current_setting('app.shop_id', true));

DROP POLICY IF EXISTS tenant_isolation ON variants;
CREATE POLICY tenant_isolation ON variants
    USING       (shop_id = current_setting('app.shop_id', true))
    WITH CHECK  (shop_id = current_setting('app.shop_id', true));

-- USING       -> lọc dòng ĐỌC ĐƯỢC (SELECT/UPDATE/DELETE)
-- WITH CHECK  -> chặn dòng GHI VÀO (INSERT/UPDATE)
--
-- Thiếu WITH CHECK thì shop A không đọc được dữ liệu shop B, nhưng vẫn
-- GHI ĐÈ được vào đó. Rò một chiều vẫn là rò.
