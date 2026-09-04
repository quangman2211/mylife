"""Adapter giả phải qua đúng bộ test như adapter thật.

Cả file chỉ có 4 dòng thân — đó chính là điểm của contract test.
Adapter KiotViet sau này cũng sẽ chỉ tốn từng này dòng.
"""

from retailops.adapters.fake import FakeAdapter

from .contract_suite import AdapterContractTests


class TestFakeAdapter(AdapterContractTests):
    def make_adapter(self, shop_id, *, fail=False):
        return FakeAdapter(shop_id, fail=fail)
