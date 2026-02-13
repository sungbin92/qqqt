import pytest

from app.engine.portfolio import Portfolio
from app.engine.position import Position


class TestPosition:
    """Position 데이터 클래스 테스트"""

    def test_market_value(self):
        pos = Position(symbol="005930", quantity=10, avg_price=70_000, current_price=72_000)
        assert pos.market_value == 720_000

    def test_add_recalculates_avg_price(self):
        """매수 추가 시 평균단가 재계산"""
        pos = Position(symbol="005930", quantity=10, avg_price=70_000, current_price=70_000)
        pos.add(10, 72_000)
        # (70,000×10 + 72,000×10) / 20 = 71,000
        assert pos.quantity == 20
        assert pos.avg_price == pytest.approx(71_000)

    def test_reduce(self):
        """부분 매도"""
        pos = Position(symbol="005930", quantity=10, avg_price=70_000, current_price=70_000)
        pos.reduce(3)
        assert pos.quantity == 7
        assert pos.avg_price == pytest.approx(70_000)  # 평균단가 유지

    def test_reduce_over_quantity_raises(self):
        pos = Position(symbol="005930", quantity=5, avg_price=70_000, current_price=70_000)
        with pytest.raises(ValueError, match="보유 수량"):
            pos.reduce(10)

    def test_is_closed(self):
        pos = Position(symbol="005930", quantity=5, avg_price=70_000, current_price=70_000)
        pos.reduce(5)
        assert pos.is_closed is True


class TestPortfolio:
    """Portfolio 클래스 테스트"""

    def test_initial_cash(self):
        """초기 현금 설정"""
        pf = Portfolio(10_000_000)
        assert pf.cash == 10_000_000
        assert pf.equity == 10_000_000
        assert len(pf.positions) == 0

    def test_buy_updates_cash_and_position(self):
        """매수 후 포지션/현금 변화"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        # 현금: 10,000,000 - (70,000×10 + 105) = 9,299,895
        assert pf.cash == pytest.approx(9_299_895)
        pos = pf.get_position("005930")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.avg_price == pytest.approx(70_000)

    def test_sell_returns_cash(self):
        """매도 후 현금 회수 + 수수료 차감"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        pf.execute_sell("005930", 10, 72_000, 108)
        # 매도 수익: 72,000×10 - 108 = 719,892
        # 현금: 9,299,895 + 719,892 = 10,019,787
        assert pf.cash == pytest.approx(10_019_787)
        assert pf.get_position("005930") is None  # 완전 청산 → 제거

    def test_partial_sell(self):
        """부분 매도"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        pf.execute_sell("005930", 3, 72_000, 54)
        pos = pf.get_position("005930")
        assert pos is not None
        assert pos.quantity == 7

    def test_equity_calculation(self):
        """평가액(equity) 계산"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        # 현금: 9,299,895 / 포지션: 10×70,000=700,000
        assert pf.equity == pytest.approx(9_999_895)

        # 가격 변동 후
        pf.update_market_prices({"005930": 75_000})
        # 포지션: 10×75,000=750,000
        assert pf.equity == pytest.approx(10_049_895)

    def test_sell_nonexistent_symbol_raises(self):
        """존재하지 않는 종목 매도 시 에러"""
        pf = Portfolio(10_000_000)
        with pytest.raises(ValueError, match="보유하지 않은 종목"):
            pf.execute_sell("999999", 10, 50_000, 100)

    def test_buy_insufficient_cash_raises(self):
        """현금 부족 시 매수 에러"""
        pf = Portfolio(100_000)
        with pytest.raises(ValueError, match="현금 부족"):
            pf.execute_buy("005930", 100, 70_000, 1_050)

    def test_get_position_weight(self):
        """포지션 비중 계산"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        # equity=9,999,895 / 포지션=700,000
        weight = pf.get_position_weight("005930")
        assert weight == pytest.approx(700_000 / 9_999_895)

    def test_get_position_weight_no_position(self):
        """미보유 종목 비중 = 0"""
        pf = Portfolio(10_000_000)
        assert pf.get_position_weight("005930") == 0.0

    def test_multiple_buys_avg_price(self):
        """동일 종목 추가 매수 시 평균단가 재계산"""
        pf = Portfolio(10_000_000)
        pf.execute_buy("005930", 10, 70_000, 105)
        pf.execute_buy("005930", 10, 72_000, 108)
        pos = pf.get_position("005930")
        assert pos.quantity == 20
        assert pos.avg_price == pytest.approx(71_000)
