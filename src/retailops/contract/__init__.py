"""T3 — Hợp đồng dữ liệu. Tài sản cốt lõi của hệ thống."""

from .base import AdapterError, NotSupported, ReadOnlyAdapter, SourceUnavailable
from .models import (
    Capabilities,
    InventorySnapshot,
    LowStockItem,
    Money,
    Product,
    SalesChannel,
    SalesSummary,
    ShopId,
    TopProduct,
    Variant,
)

__all__ = [
    "AdapterError", "NotSupported", "ReadOnlyAdapter", "SourceUnavailable",
    "Capabilities", "InventorySnapshot", "LowStockItem", "Money", "Product",
    "SalesChannel", "SalesSummary", "ShopId", "TopProduct", "Variant",
]
