"""Repository — đường DUY NHẤT để tầng trên chạm dữ liệu.

Chú ý câu SQL bên dưới: KHÔNG câu nào có `WHERE shop_id = ...`.
RLS tự thêm. Người viết truy vấn không phải nghĩ về đa khách hàng —
và cái gì không phải nhớ thì không quên được.

Đó là mục tiêu thiết kế của cả tầng này: làm cho việc viết đúng KHÔNG TỐN
CÔNG HƠN viết sai. Quy ước nào đòi lập trình viên phải cố gắng thì quy ước
đó sẽ bị phá, sớm hay muộn.
"""

from __future__ import annotations

from ..contract.models import Product, ShopId, Variant
from .tenancy import ShopScope


class ProductRepository:
    def __init__(self, scope: ShopScope) -> None:
        # Nhận ShopScope chứ không nhận Connection: không có cách nào tạo
        # repository "chưa gắn shop". Kiểu dữ liệu ép, không phải quy ước.
        self._scope = scope

    @property
    def shop_id(self) -> ShopId:
        return self._scope.shop_id

    def search(self, query: str, limit: int = 20) -> list[Product]:
        rows = self._scope.query(
            """
            SELECT id, name, price, total_stock, description
              FROM products
             WHERE (%s = '' OR name ILIKE '%%' || %s || '%%')
             ORDER BY name
             LIMIT %s
            """,
            (query, query, limit),
        )
        return [self._build(r) for r in rows]

    def get(self, product_id: str) -> Product | None:
        rows = self._scope.query(
            "SELECT id, name, price, total_stock, description FROM products WHERE id = %s",
            (product_id,),
        )
        return self._build(rows[0]) if rows else None

    def count(self) -> int:
        """RLS áp cho CẢ hàm tổng hợp.

        Đáng test riêng: nhiều người tưởng RLS chỉ lọc dòng trả về, nên
        COUNT/SUM vẫn đếm cả bảng. Không phải — nhưng phải có test chứng
        minh, vì nếu sai thì shop A đoán được shop B có bao nhiêu hàng.
        Rò con số cũng là rò.
        """
        return self._scope.query("SELECT count(*) FROM products")[0][0]

    def upsert(self, product: Product) -> None:
        """Ghi shop_id TƯỜNG MINH, dù RLS đã có WITH CHECK.

        Vì sao vẫn ghi khi DB đã tự chặn: cột shop_id là NOT NULL, phải có
        giá trị. Và ghi đúng giá trị từ scope thì WITH CHECK luôn qua —
        ghi sai thì DB đá ra ngay. Hai cơ chế cùng nói một điều, và đó là
        chủ ý: một cái hỏng thì cái kia còn.
        """
        self._scope.execute(
            """
            INSERT INTO products (shop_id, id, name, price, total_stock, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (shop_id, id) DO UPDATE SET
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                total_stock = EXCLUDED.total_stock,
                description = EXCLUDED.description,
                synced_at = now()
            """,
            (self.shop_id, product.id, product.name, product.price,
             product.total_stock, product.description),
        )
        for v in product.variants:
            self._scope.execute(
                """
                INSERT INTO variants (shop_id, id, product_id, sku, size, color, price, stock)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (shop_id, id) DO UPDATE SET
                    sku = EXCLUDED.sku, size = EXCLUDED.size, color = EXCLUDED.color,
                    price = EXCLUDED.price, stock = EXCLUDED.stock
                """,
                (self.shop_id, v.id, product.id, v.sku, v.size, v.color, v.price, v.stock),
            )

    def _load_variants(self, product_id: str) -> tuple[Variant, ...]:
        rows = self._scope.query(
            "SELECT id, sku, size, color, price, stock FROM variants "
            "WHERE product_id = %s ORDER BY id",
            (product_id,),
        )
        return tuple(
            Variant(id=r[0], sku=r[1], size=r[2], color=r[3], price=r[4], stock=r[5])
            for r in rows
        )

    def _build(self, row: tuple) -> Product:
        pid, name, price, total_stock, description = row
        variants = self._load_variants(pid)

        # Bất biến số 4 của hợp đồng, ép lại ở tầng này.
        # Vì sao lặp: dữ liệu có thể vào DB bằng đường khác (import, sửa tay,
        # migration cũ) chứ không chỉ qua upsert() ở trên. Chỗ nào ĐỌC ra
        # cũng phải bảo đảm bất biến, không chỉ chỗ GHI vào.
        if any(v.stock is None for v in variants):
            total_stock = None

        return Product(
            id=pid, name=name, price=price, total_stock=total_stock,
            description=description, variants=variants,
        )
