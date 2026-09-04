"""Hình dạng dữ liệu của Hợp đồng (T3).

Đây là NGÔN NGỮ CHUNG giữa lõi agent (T4) và mọi nguồn dữ liệu (T0).

Nguyên tắc (blueprint §3.1):
  1. Thiết kế cho CÁI AGENT CẦN BIẾT, không phải cái KiotViet/Woo có sẵn.
  2. Không để lộ khái niệm riêng của bất kỳ nền tảng nào lên tầng này.
     -> Không có trường `kiotviet_id`, không có `wc_post_id`, không có `raw`.
        Cần dữ liệu gốc để debug thì log ở T1, đừng mang lên đây.
  3. Mọi trường tuỳ chọn phải hỏi được qua get_capabilities().
  4. Mọi thứ trả về tồn kho BẮT BUỘC kèm thời điểm.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# Tiền: số nguyên VNĐ, không phần lẻ.
# KHÔNG dùng float cho tiền — 0.1 + 0.2 != 0.3 và sai số tích luỹ qua mỗi
# phép cộng doanh thu. Giá bán lẻ ở VN không bao giờ lẻ đến đồng.
Money = int

# Định danh shop trong hệ thống của MÌNH (không phải id bên KiotViet).
ShopId = str


class _Frozen(BaseModel):
    """Bất biến + cấm trường lạ.

    frozen=True: object đã tạo thì không sửa được. Nếu một hàm ở tầng trên
        lỡ tay đổi `product.price` thì nổ ngay tại chỗ, thay vì âm thầm
        làm sai con số agent đọc ra.
    extra='forbid': adapter trả thừa trường -> lỗi ngay lúc parse. Đây là
        cách chặn khái niệm riêng của nền tảng rò lên T3.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class Capabilities(_Frozen):
    """Adapter tự khai báo NÓ LÀM ĐƯỢC GÌ.

    Đây là hàm quan trọng nhất của hợp đồng. Nhờ nó, lõi agent tự tắt tool,
    tắt dòng prompt, tắt luật grounding tương ứng — không cần cấu hình tay
    cho từng khách.

    Ví dụ: adapter Excel khai realtime_inventory=False -> agent tự đổi cách
    nói từ "còn 3 đôi" sang "theo dữ liệu ngày 02/09 thì còn hàng".
    Agent TỰ BIẾT MÌNH MÙ.

    Vì sao là các trường bool cố định, không phải set[str] các tên tính năng:
        set[str] thì gõ sai một chữ ("realtime_inv") sẽ âm thầm thành "không
        có" và không ai biết. Trường cố định thì thiếu là Pydantic báo lỗi
        ngay lúc adapter khởi tạo.
    """

    # --- đọc ---
    has_variants: bool  # phân biệt được size/màu thành bản ghi riêng?
    has_inventory: bool  # đọc được số tồn?
    realtime_inventory: bool  # số tồn là NGAY BÂY GIỜ hay ảnh chụp cũ?
    has_cost_price: bool  # đọc được giá vốn? (nhạy cảm — mặc định giấu NV)
    has_orders: bool
    has_customers: bool

    # --- ghi (P2, chưa dùng ở MVP) ---
    can_write_price: bool = False
    can_write_stock: bool = False
    can_create_product: bool = False

    # --- vận hành ---
    # Nhịp dữ liệu cũ nhất có thể. 0 = realtime.
    # Lõi dùng số này để quyết định có nên cảnh báo "dữ liệu có thể đã cũ".
    max_staleness_seconds: int = Field(ge=0)


class Variant(_Frozen):
    """Một biến thể bán được: một size, một màu cụ thể."""

    id: str
    sku: str | None = None
    size: str | None = None
    color: str | None = None
    price: Money | None = None

    # None = KHÔNG BIẾT. 0 = ĐÃ KIỂM, HẾT HÀNG.
    # Đây là chỗ dễ gây lỗi 🔴 nhất trong toàn hệ thống (xem Q2.5).
    # Gộp hai giá trị này làm một -> agent nói "hết hàng" khi thực ra còn.
    # Kiểu dữ liệu phải ép phân biệt, không trông chờ dev nhớ.
    stock: int | None = None


class Product(_Frozen):
    id: str
    name: str
    price: Money | None = None
    variants: tuple[Variant, ...] = ()
    image_urls: tuple[str, ...] = ()
    description: str | None = None

    # Tổng tồn của mọi biến thể. None nếu có BẤT KỲ biến thể nào không biết
    # tồn — vì tổng của "3 + không biết" không phải là 3.
    total_stock: int | None = None

    def is_definitely_out_of_stock(self) -> bool:
        """Chỉ True khi CHẮC CHẮN hết. Không biết -> False.

        Đặt tên dài dòng là cố ý: đọc câu lệnh `if p.is_definitely_out_of_stock()`
        thì không ai hiểu nhầm thành "không có hàng".
        """
        return self.total_stock == 0


class InventorySnapshot(_Frozen):
    """Ảnh chụp tồn kho tại MỘT thời điểm.

    Vì sao bắt buộc có as_of (blueprint §3.1 nguyên tắc 4):
        Agent nói "còn 3 đôi" mà số đó lấy từ bản đồng bộ 6 tiếng trước thì
        đó là nói dối, dù không cố ý. Có as_of thì lõi tự chọn được cách nói.
    """

    product_id: str
    by_variant: dict[str, int | None]
    as_of: datetime
    is_realtime: bool

    def age_seconds(self, now: datetime) -> float:
        return (now - self.as_of).total_seconds()


class SalesChannel(StrEnum):
    """Kênh bán. Cố ý là danh sách đóng.

    Nếu để str tự do, mỗi adapter sẽ đặt một kiểu ("FB", "facebook",
    "Facebook") và mọi báo cáo gộp theo kênh sẽ sai. Adapter gặp kênh lạ
    thì map về OTHER, không tự bịa tên mới.
    """

    POS = "pos"  # bán tại quầy
    WEBSITE = "website"
    FACEBOOK = "facebook"
    ZALO = "zalo"
    MARKETPLACE = "marketplace"  # Shopee, Lazada, TikTok Shop
    OTHER = "other"


class TopProduct(_Frozen):
    product_id: str
    name: str
    quantity_sold: int
    revenue: Money


class SalesSummary(_Frozen):
    from_date: datetime
    to_date: datetime
    revenue: Money
    order_count: int
    top_products: tuple[TopProduct, ...] = ()
    revenue_by_channel: dict[SalesChannel, Money] = Field(default_factory=dict)

    @property
    def avg_order_value(self) -> Money:
        """Tính, không lưu.

        Vì sao không để adapter tự tính rồi trả về: hai adapter sẽ làm tròn
        khác nhau, và sẽ có adapter tính sai. Cái gì suy ra được từ dữ liệu
        khác thì đừng lưu — đó là một nguồn chân lý thứ hai chờ lệch nhau.
        """
        if self.order_count == 0:
            return 0
        return self.revenue // self.order_count


class LowStockItem(_Frozen):
    product_id: str
    name: str
    variant_id: str | None
    stock: int
    sold_last_30_days: int

    @property
    def days_of_cover(self) -> float | None:
        """Còn bán được mấy ngày nữa với tốc độ hiện tại.

        None khi 30 ngày qua không bán được cái nào — lúc đó "còn mấy ngày"
        là vô nghĩa (chia cho 0), và đó là hàng TỒN chứ không phải hàng
        SẮP HẾT. Hai vấn đề khác nhau, đừng trộn.
        """
        if self.sold_last_30_days <= 0:
            return None
        return self.stock / (self.sold_last_30_days / 30)
