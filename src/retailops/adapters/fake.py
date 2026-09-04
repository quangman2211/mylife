"""Adapter giả — chạy hoàn toàn trong bộ nhớ.

VÌ SAO ĐÂY LÀ FILE ĐÁNG GIÁ, KHÔNG PHẢI CODE VỨT ĐI:

  1. Gỡ thế bí Q0.1. Chưa biết API KiotViet ra sao vẫn dựng và đo được
     toàn bộ lõi agent (T4) — tức là trả lời được Q2.1, Q2.5, Q2.6, Q0.5,
     Q3.1, Q3.3. Đó là 6 câu hỏi ở CỔNG 2 và 3, mở khoá bằng một file.

  2. Là bài kiểm tra ngược cho chính hợp đồng. Hợp đồng nào không viết nổi
     một bản giả thì hợp đồng đó thiết kế sai.

  3. Test chạy trong mili-giây, không cần mạng, không tốn tiền API.

DỮ LIỆU CỐ Ý XẤU. Có đủ: thiếu giá, thiếu tồn, không ảnh, không mô tả,
biến thể mù tồn kho. Nếu dữ liệu giả toàn hàng đẹp thì code viết ra sẽ
chết đúng ngày cắm dữ liệu thật.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..contract.base import ReadOnlyAdapter, SourceUnavailable
from ..contract.models import (
    Capabilities,
    InventorySnapshot,
    LowStockItem,
    Product,
    SalesChannel,
    SalesSummary,
    ShopId,
    TopProduct,
    Variant,
)


def _sample_products() -> list[Product]:
    """Danh mục mẫu kiểu shop giày trẻ em.

    Mỗi mục cố ý mang một khiếm khuyết khác nhau — xem comment từng dòng.
    """
    return [
        # Ca thường: đủ giá, đủ tồn, đủ ảnh. Đây là ca DỄ.
        Product(
            id="SP001",
            name="Giày thể thao bé trai Velcro",
            price=285_000,
            image_urls=("https://example.invalid/sp001.jpg",),
            description="Đế cao su chống trượt, quai dán tiện cho bé tự đi.",
            variants=(
                Variant(id="SP001-26", sku="SP001-26", size="26", color="Xanh", price=285_000, stock=4),
                Variant(id="SP001-27", sku="SP001-27", size="27", color="Xanh", price=285_000, stock=0),
                Variant(id="SP001-28", sku="SP001-28", size="28", color="Xanh", price=285_000, stock=11),
            ),
            total_stock=15,
        ),
        # Ca khó 1: MỘT biến thể không biết tồn.
        # -> total_stock phải là None, KHÔNG phải 7.
        #    Vì "3 + 4 + không biết" không phải là 7.
        Product(
            id="SP002",
            name="Dép quai hậu bé gái",
            price=155_000,
            image_urls=("https://example.invalid/sp002.jpg",),
            description=None,  # thiếu mô tả — rất phổ biến ngoài thực tế
            variants=(
                Variant(id="SP002-25", sku="SP002-25", size="25", color="Hồng", price=155_000, stock=3),
                Variant(id="SP002-26", sku="SP002-26", size="26", color="Hồng", price=155_000, stock=4),
                Variant(id="SP002-27", sku="SP002-27", size="27", color="Hồng", price=155_000, stock=None),
            ),
            total_stock=None,
        ),
        # Ca khó 2: THIẾU GIÁ hoàn toàn, không ảnh, không biến thể.
        # Agent tuyệt đối không được bịa giá cho mặt hàng này.
        Product(
            id="SP003",
            name="Giày búp bê bé gái size 29 màu đỏ",  # size + màu nhét trong TÊN
            price=None,
            variants=(),
            total_stock=None,
        ),
        # Ca khó 3: hàng TỒN LÂU — còn nhiều nhưng không ai mua.
        # Khác hẳn "sắp hết". Hai vấn đề, hai cách xử lý.
        Product(
            id="SP004",
            name="Ủng đi mưa trẻ em",
            price=198_000,
            image_urls=("https://example.invalid/sp004.jpg",),
            description="Cao su mềm, chống thấm.",
            variants=(
                Variant(id="SP004-30", sku="SP004-30", size="30", color="Vàng", price=198_000, stock=42),
            ),
            total_stock=42,
        ),
    ]


@dataclass(frozen=True)
class _FakeOrder:
    """Một đơn hàng. lines = [(product_id, tên, số lượng, đơn giá)]."""

    date: datetime
    channel: SalesChannel
    lines: tuple[tuple[str, str, int, int], ...]


def _sample_orders() -> list[_FakeOrder]:
    """Đơn hàng tháng 8/2026, rải trên nhiều kênh.

    Cố ý đặt trong MỘT tháng cụ thể: hỏi khoảng ngoài tháng đó phải ra 0.
    Đó là điều bản trước làm sai.
    """
    ch = SalesChannel
    giay = "Giày thể thao bé trai Velcro"
    dep = "Dép quai hậu bé gái"
    ung = "Ủng đi mưa trẻ em"
    return [
        _FakeOrder(datetime(2026, 8, 3, 9, 20), ch.POS,
                   (("SP001", giay, 2, 285_000),)),
        _FakeOrder(datetime(2026, 8, 7, 14, 5), ch.FACEBOOK,
                   (("SP001", giay, 1, 285_000), ("SP002", dep, 2, 155_000))),
        _FakeOrder(datetime(2026, 8, 12, 11, 0), ch.POS,
                   (("SP002", dep, 3, 155_000),)),
        _FakeOrder(datetime(2026, 8, 18, 20, 45), ch.MARKETPLACE,
                   (("SP001", giay, 4, 285_000),)),
        _FakeOrder(datetime(2026, 8, 23, 8, 30), ch.ZALO,
                   (("SP004", ung, 1, 198_000),)),
        _FakeOrder(datetime(2026, 8, 29, 17, 15), ch.FACEBOOK,
                   (("SP001", giay, 2, 285_000), ("SP004", ung, 1, 198_000))),
    ]


class FakeAdapter(ReadOnlyAdapter):
    """Nguồn dữ liệu trong bộ nhớ, hành xử ĐÚNG như hợp đồng.

    Tham số dựng:
        realtime: giả lập nguồn realtime (KiotViet API) hay ảnh chụp cũ
            (file Excel). Đổi cờ này để kiểm tra lõi có TỰ ĐỔI CÁCH NÓI
            theo capabilities không — đó chính là điều get_capabilities()
            sinh ra để phục vụ.
        fail: bật lên thì mọi lời gọi ném SourceUnavailable. Dùng để test
            luồng hỏng. Đường code xử lý sự cố mà không có test thì ngày
            sự cố thật nó cũng hỏng nốt.
    """

    def __init__(
        self,
        shop_id: ShopId,
        *,
        realtime: bool = True,
        fail: bool = False,
        now: datetime | None = None,
    ) -> None:
        super().__init__(shop_id)
        self._realtime = realtime
        self._fail = fail
        # Mặc định GIỜ THẬT. Bản giả mô phỏng nguồn sống thì phải sống.
        # Đóng băng thời gian là việc test CHỦ ĐỘNG làm (truyền now=...),
        # không phải hành vi mặc định — nếu không, adapter khai realtime
        # sẽ trả dữ liệu cũ vài tiếng mà tự nó không biết.
        self._now = now or datetime.now()
        self._products = {p.id: p for p in _sample_products()}

    def _guard(self) -> None:
        if self._fail:
            raise SourceUnavailable(f"nguồn của shop {self.shop_id} đang không trả lời")

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            has_variants=True,
            has_inventory=True,
            realtime_inventory=self._realtime,
            has_cost_price=False,  # KiotViet có, nhưng chưa chắc API cho đọc
            has_orders=True,
            has_customers=False,
            max_staleness_seconds=0 if self._realtime else 24 * 3600,
        )

    def search_products(self, query: str, limit: int = 20) -> list[Product]:
        self._guard()
        q = query.strip().lower()
        if not q:
            return list(self._products.values())[:limit]
        # Tìm ngây thơ. Bản thật cần Postgres FTS + unaccent (dấu tiếng Việt).
        # Cố ý để đơn giản: đây là test double, không phải công cụ tìm kiếm.
        hits = [p for p in self._products.values() if q in p.name.lower()]
        return hits[:limit]

    def get_product(self, product_id: str) -> Product | None:
        self._guard()
        return self._products.get(product_id)

    def get_inventory(self, product_id: str) -> InventorySnapshot | None:
        self._guard()
        product = self._products.get(product_id)
        if product is None:
            return None
        as_of = self._now if self._realtime else self._now - timedelta(hours=8)
        return InventorySnapshot(
            product_id=product_id,
            by_variant={v.id: v.stock for v in product.variants},
            as_of=as_of,
            is_realtime=self._realtime,
        )

    def get_low_stock(self, threshold: int) -> list[LowStockItem]:
        self._guard()
        sold_30d = {"SP001-26": 18, "SP001-27": 22, "SP002-25": 9, "SP004-30": 0}
        out: list[LowStockItem] = []
        for product in self._products.values():
            for variant in product.variants:
                # Biến thể KHÔNG BIẾT tồn thì bỏ qua, không đoán.
                # Đưa nó vào danh sách "sắp hết" là bịa.
                if variant.stock is None or variant.stock > threshold:
                    continue
                out.append(
                    LowStockItem(
                        product_id=product.id,
                        name=product.name,
                        variant_id=variant.id,
                        stock=variant.stock,
                        sold_last_30_days=sold_30d.get(variant.id, 0),
                    )
                )
        return sorted(out, key=lambda i: i.stock)

    def get_sales_summary(self, from_date: datetime, to_date: datetime) -> SalesSummary:
        """Tính TỪ đơn hàng, không hardcode con số tổng.

        Bản trước hardcode revenue=12.450.000 cho mọi khoảng thời gian — hỏi
        doanh thu năm 2099 nó vẫn trả 37 đơn. Bộ test hợp đồng bắt được.

        Đó là kiểu lỗi tệ nhất của test double: nó KHÔNG hỏng lúc dev, nó
        hỏng đúng ngày cắm dữ liệu thật — vì nguồn thật CÓ lọc theo ngày.
        Bản giả phải giả lập cả HÀNH VI, không chỉ giả lập kết quả.
        """
        self._guard()
        orders = [o for o in _sample_orders() if from_date <= o.date < to_date]

        revenue = 0
        by_channel: dict[SalesChannel, int] = {}
        per_product: dict[str, tuple[str, int, int]] = {}

        for order in orders:
            for product_id, name, qty, unit_price in order.lines:
                line_total = qty * unit_price
                revenue += line_total
                by_channel[order.channel] = by_channel.get(order.channel, 0) + line_total
                pname, pqty, prev = per_product.get(product_id, (name, 0, 0))
                per_product[product_id] = (pname, pqty + qty, prev + line_total)

        top = tuple(
            TopProduct(product_id=pid, name=n, quantity_sold=q, revenue=r)
            for pid, (n, q, r) in sorted(
                per_product.items(), key=lambda kv: kv[1][2], reverse=True
            )[:5]
        )
        return SalesSummary(
            from_date=from_date,
            to_date=to_date,
            revenue=revenue,
            order_count=len(orders),
            top_products=top,
            revenue_by_channel=by_channel,
        )
