"""Bộ kiểm thử HỢP ĐỒNG — dùng chung cho MỌI adapter.

CÁCH DÙNG. Viết adapter mới xong, thêm đúng 4 dòng:

    from tests.contract_suite import AdapterContractTests

    class TestKiotViet(AdapterContractTests):
        def make_adapter(self, shop_id, *, fail=False):
            return KiotVietAdapter(shop_id, ...)

-> Lập tức có toàn bộ test dưới đây. Không copy, không sót.

VÌ SAO LÀM THẾ NÀY:
  Sẽ có 5+ adapter. Mỗi adapter một bộ test riêng thì chúng sẽ lệch nhau,
  và adapter viết sau luôn thiếu test mà adapter viết trước có. Viết một
  lần cho INTERFACE thì adapter mới không có đường nào thiếu.

  Hệ quả quan trọng hơn: đây là bộ công cụ giao cho KHÁCH tự viết adapter
  (blueprint §3.2, mô hình "công của bạn = 0"). Khách chạy pytest, tự biết
  mình thiếu gì, không cần hỏi.

  Và: "adapter hợp lệ" từ nay có ĐỊNH NGHĨA CHÍNH XÁC — là "qua bộ test
  này", chứ không phải "trông có vẻ đúng".
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from retailops.contract import (
    Capabilities,
    InventorySnapshot,
    Product,
    ReadOnlyAdapter,
    SalesSummary,
    SourceUnavailable,
)


class AdapterContractTests:
    """Kế thừa class này và cài đặt make_adapter()."""

    # --- lớp con phải cài đặt ---

    def make_adapter(self, shop_id: str, *, fail: bool = False) -> ReadOnlyAdapter:
        raise NotImplementedError

    # --- id sản phẩm có thật trong nguồn, để test truy vấn đích danh ---
    known_product_id: str = "SP001"

    @pytest.fixture
    def adapter(self) -> ReadOnlyAdapter:
        return self.make_adapter("shop-test")

    # ================= NHÓM 1: cách ly theo shop =================
    # Đây là rủi ro R1 — rủi ro duy nhất có thể chấm dứt công ty.

    def test_shop_id_gan_luc_khoi_tao(self, adapter):
        assert adapter.shop_id == "shop-test"

    def test_shop_id_khong_doi_duoc_sau_khi_tao(self, adapter):
        """Đổi được shop_id = một instance phục vụ hai shop = rò dữ liệu."""
        with pytest.raises(AttributeError):
            adapter.shop_id = "shop-khac"

    def test_shop_id_rong_bi_tu_choi_ngay(self):
        """Chặn tại constructor, không để nó chạy tiếp rồi hỏng ở chỗ khác."""
        with pytest.raises(ValueError):
            self.make_adapter("")

    # ================= NHÓM 2: khai báo năng lực =================

    def test_get_capabilities_tra_ve_day_du(self, adapter):
        caps = adapter.get_capabilities()
        assert isinstance(caps, Capabilities)
        assert caps.max_staleness_seconds >= 0

    def test_realtime_thi_staleness_bang_0(self, adapter):
        """Khai realtime nhưng vẫn cho phép dữ liệu cũ 8 tiếng là tự mâu thuẫn."""
        caps = adapter.get_capabilities()
        if caps.realtime_inventory:
            assert caps.max_staleness_seconds == 0

    # ================= NHÓM 3: tìm kiếm =================

    def test_khong_tim_thay_tra_list_rong_khong_raise(self, adapter):
        """'Không có kết quả' là kết quả hợp lệ, không phải sự cố."""
        assert adapter.search_products("xyzzy-khong-ton-tai-abc123") == []

    def test_search_ton_trong_limit(self, adapter):
        assert len(adapter.search_products("", limit=2)) <= 2

    def test_search_tra_ve_dung_kieu(self, adapter):
        for p in adapter.search_products("", limit=5):
            assert isinstance(p, Product)

    # ================= NHÓM 4: sản phẩm =================

    def test_id_khong_ton_tai_tra_None(self, adapter):
        assert adapter.get_product("KHONG-CO-ID-NAY") is None

    def test_lay_duoc_san_pham_co_that(self, adapter):
        p = adapter.get_product(self.known_product_id)
        assert p is not None and p.id == self.known_product_id

    def test_product_bat_bien(self, adapter):
        """frozen=True: tầng trên lỡ tay sửa giá thì nổ ngay, không âm thầm."""
        p = adapter.get_product(self.known_product_id)
        with pytest.raises(ValidationError):
            p.price = 1

    # ========== NHÓM 5: BẤT BIẾN QUAN TRỌNG NHẤT ==========

    def test_bien_the_mu_ton_thi_tong_ton_phai_la_None(self, adapter):
        """'3 + 4 + không biết' KHÔNG phải là 7.

        Adapter nào cộng bừa sẽ khiến agent nói 'còn 7 đôi' — con số bịa.
        Đó là lỗi 🔴 mà Q2.5 yêu cầu phải bằng 0. Test này là cái chặn.
        """
        for p in adapter.search_products("", limit=100):
            if any(v.stock is None for v in p.variants):
                assert p.total_stock is None, (
                    f"{p.id}: có biến thể không biết tồn nhưng total_stock="
                    f"{p.total_stock}. Phải là None."
                )

    def test_tong_ton_khop_voi_tong_bien_the(self, adapter):
        """Khi BIẾT hết mọi biến thể thì tổng phải đúng bằng tổng cộng lại."""
        for p in adapter.search_products("", limit=100):
            if p.variants and all(v.stock is not None for v in p.variants):
                assert p.total_stock == sum(v.stock for v in p.variants), p.id

    def test_khong_bao_gio_ton_am(self, adapter):
        for p in adapter.search_products("", limit=100):
            assert p.total_stock is None or p.total_stock >= 0
            for v in p.variants:
                assert v.stock is None or v.stock >= 0

    def test_gia_khong_am(self, adapter):
        for p in adapter.search_products("", limit=100):
            assert p.price is None or p.price >= 0

    # ================= NHÓM 6: tồn kho + độ tươi =================

    def test_inventory_luon_kem_thoi_diem(self, adapter):
        """Nguyên tắc 4 của hợp đồng. Không có as_of thì con số là lời nói dối."""
        snap = adapter.get_inventory(self.known_product_id)
        assert isinstance(snap, InventorySnapshot)
        assert isinstance(snap.as_of, datetime)

    def test_do_cu_khong_vuot_qua_muc_da_khai(self, adapter):
        """Adapter khai 'tối đa cũ 1 tiếng' thì không được trả dữ liệu 8 tiếng.

        Không có test này thì khai báo năng lực chỉ là lời hứa suông, và lõi
        agent đang tin vào một lời hứa không ai kiểm.
        """
        caps = adapter.get_capabilities()
        snap = adapter.get_inventory(self.known_product_id)
        assert snap is not None
        # +60s dung sai cho lệch đồng hồ / thời gian gọi API.
        assert snap.age_seconds(datetime.now()) <= caps.max_staleness_seconds + 60

    def test_inventory_cua_id_khong_ton_tai_tra_None(self, adapter):
        assert adapter.get_inventory("KHONG-CO-ID-NAY") is None

    # ================= NHÓM 7: hàng sắp hết =================

    def test_low_stock_khong_chua_bien_the_mu_ton(self, adapter):
        """Không biết tồn thì không được đoán là sắp hết. Đoán = bịa."""
        for item in adapter.get_low_stock(threshold=5):
            assert item.stock is not None and item.stock <= 5

    def test_low_stock_nguong_0_chi_ra_hang_da_het(self, adapter):
        for item in adapter.get_low_stock(threshold=0):
            assert item.stock == 0

    # ================= NHÓM 8: doanh thu =================

    def test_khong_co_don_van_tra_so_khong_chu_khong_None(self, adapter):
        """Bảng tin luôn cần một con số để hiện. Trả None chỉ đẩy việc đi chỗ khác."""
        future = datetime(2099, 1, 1)
        s = adapter.get_sales_summary(future, future + timedelta(days=1))
        assert isinstance(s, SalesSummary)
        assert s.revenue >= 0 and s.order_count >= 0

    def test_don_trung_binh_khong_chia_cho_0(self, adapter):
        future = datetime(2099, 1, 1)
        assert adapter.get_sales_summary(future, future + timedelta(days=1)).avg_order_value == 0

    def test_doanh_thu_theo_kenh_khong_vuot_tong(self, adapter):
        s = adapter.get_sales_summary(datetime(2026, 8, 1), datetime(2026, 9, 1))
        if s.revenue_by_channel:
            assert sum(s.revenue_by_channel.values()) <= s.revenue

    # ================= NHÓM 9: khi nguồn hỏng =================

    def test_nguon_hong_nem_SourceUnavailable_chu_khong_phai_loi_thu_vien(self):
        """Lõi phải xử lý được 'nguồn hỏng' mà không cần biết đó là HTTP hay file.

        Nếu để requests.HTTPError bay thẳng lên, lõi buộc phải import requests
        -> khái niệm HTTP rò lên T4, phá nguyên tắc 2 của hợp đồng.
        """
        broken = self.make_adapter("shop-test", fail=True)
        with pytest.raises(SourceUnavailable):
            broken.search_products("giày")

    def test_nguon_hong_KHONG_duoc_gia_vo_la_khong_co_hang(self):
        """Ca nguy hiểm nhất: nguồn sập, adapter trả [] -> agent nói 'hết hàng'.

        Khách bỏ đi, shop mất đơn, và không ai biết vì sao. Hỏng phải KÊU.
        """
        broken = self.make_adapter("shop-test", fail=True)
        for call in (
            lambda: broken.get_product("SP001"),
            lambda: broken.get_inventory("SP001"),
            lambda: broken.get_low_stock(5),
        ):
            with pytest.raises(SourceUnavailable):
                call()
