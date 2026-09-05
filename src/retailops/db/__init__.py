"""T2 — Kho chuẩn hoá, cách ly đa khách hàng."""

from .repository import ProductRepository
from .tenancy import ShopScope, TenancyError, current_scope, shop_scope

__all__ = ["ProductRepository", "ShopScope", "TenancyError", "current_scope", "shop_scope"]
