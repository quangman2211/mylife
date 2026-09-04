"""Hợp đồng dữ liệu (T3) — phần giao diện.

MỌI nguồn dữ liệu (KiotViet, WooCommerce, Excel, web tự code) đều hiện ra
với lõi agent dưới đúng hình dạng này. Lõi KHÔNG BAO GIỜ biết nó đang nói
chuyện với nền tảng nào.

Đó là lý do đổi từ KiotViet sang Sapo không phải viết lại lõi — chỉ viết
thêm một class kế thừa ReadOnlyAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .models import (
    Capabilities,
    InventorySnapshot,
    LowStockItem,
    Product,
    SalesSummary,
    ShopId,
)


class AdapterError(Exception):
    """Gốc của mọi lỗi adapter.

    Vì sao cần cây lỗi riêng thay vì để requests.HTTPError bay lên:
        Lõi agent phải xử lý được "nguồn đang hỏng" mà KHÔNG cần biết nguồn
        đó là HTTP, là file Excel, hay là ODBC. Nếu để lỗi của thư viện bay
        thẳng lên, lõi buộc phải import requests -> khái niệm HTTP rò lên
        T4, phá nguyên tắc 2.
    """


class SourceUnavailable(AdapterError):
    """Nguồn không trả lời (mạng hỏng, API sập, hết rate limit).

    Lõi phải nói "em chưa tra được", TUYỆT ĐỐI không được coi như "không có".
    """


class NotSupported(AdapterError):
    """Adapter không làm được việc này.

    Đáng lẽ không bao giờ xảy ra: lõi phải hỏi get_capabilities() trước.
    Nếu ngoại lệ này bị ném ra tức là CÓ BUG Ở LÕI, không phải lỗi người dùng.
    """


class ReadOnlyAdapter(ABC):
    """Adapter chỉ đọc — đủ cho toàn bộ MVP.

    Nhóm ghi (stage_*/apply_*) cố ý KHÔNG nằm ở đây: nó là P2 và đang bị
    Q0.1 chặn (chưa biết KiotViet có cho ghi không). Khi nào mở, tạo
    WritableAdapter(ReadOnlyAdapter) riêng — adapter chỉ đọc không phải
    implement một đống hàm rồi raise NotImplementedError.

        Quy tắc chung: interface mà implementer buộc phải để trống một nửa
        là interface bị chia sai. Tách nhỏ ra.

    --- shop_id nằm ở constructor, không ở từng hàm ---
    Một instance = một shop. Credential gắn vào instance.
    Dùng nhầm instance của shop khác -> KiotViet trả 401 vì sai token,
    tức là NGUỒN BÊN KIA tự chặn hộ mình.

    Điều này KHÔNG áp dụng cho tầng repository (T2 — DB của mình). Ở đó một
    DB chứa mọi shop, quên WHERE shop_id là lặng lẽ trả dữ liệu shop khác,
    không ai chặn hộ. Tầng đó cần cơ chế mạnh hơn hẳn — xem bước sau.
    """

    def __init__(self, shop_id: ShopId) -> None:
        if not shop_id:
            # Chuỗi rỗng là lỗi lập trình, không phải lỗi dữ liệu.
            # Chặn ngay lúc tạo, đừng để nó chạy tiếp rồi hỏng ở chỗ khác.
            raise ValueError("shop_id không được rỗng")
        self._shop_id = shop_id

    @property
    def shop_id(self) -> ShopId:
        """Chỉ đọc — không có setter.

        Nếu đổi được shop_id sau khi tạo thì một instance có thể phục vụ
        hai shop, và toàn bộ lập luận an toàn ở trên sụp.
        """
        return self._shop_id

    # ---------- năng lực ----------

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        """Adapter làm được gì. Lõi gọi hàm này TRƯỚC mọi thứ khác."""

    # ---------- sản phẩm ----------

    @abstractmethod
    def search_products(self, query: str, limit: int = 20) -> list[Product]:
        """Tìm theo tên/mã. Không tìm thấy -> trả list rỗng, KHÔNG raise.

        Vì sao rỗng chứ không phải ngoại lệ: "không có kết quả" là kết quả
        hợp lệ, không phải sự cố. Dùng ngoại lệ cho luồng bình thường khiến
        chỗ gọi phải bọc try/except quanh mọi thứ và rồi sẽ nuốt luôn cả
        lỗi thật.
        """

    @abstractmethod
    def get_product(self, product_id: str) -> Product | None:
        """None khi không tồn tại.

        None ở đây an toàn vì kiểu trả về là `Product | None` — type checker
        bắt chỗ gọi phải xử lý. Khác với stock=None ở models.py, chỗ đó None
        mang nghĩa "không biết" nên phải ghi rõ bằng comment.
        """

    @abstractmethod
    def get_inventory(self, product_id: str) -> InventorySnapshot | None:
        """Bắt buộc kèm as_of. Xem models.InventorySnapshot."""

    @abstractmethod
    def get_low_stock(self, threshold: int) -> list[LowStockItem]:
        """Hàng sắp hết. Chỉ gọi khi capabilities.has_inventory."""

    # ---------- bán hàng ----------

    @abstractmethod
    def get_sales_summary(self, from_date: datetime, to_date: datetime) -> SalesSummary:
        """Tổng hợp doanh thu trong khoảng [from_date, to_date].

        Không có đơn nào -> trả SalesSummary với revenue=0, order_count=0.
        KHÔNG trả None: chỗ gọi là bảng tin, nó luôn cần một con số để hiện.
        Trả None chỉ đẩy việc xử lý sang chỗ khác.
        """
