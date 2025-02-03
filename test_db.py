import unittest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class TestDatabaseConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Устанавливаем строку подключения
        cls.DATABASE_URL = "postgresql+psycopg2://root:123456er@127.0.0.1:5432/statix"
        cls.engine = create_engine(cls.DATABASE_URL)
        cls.Session = sessionmaker(bind=cls.engine)

    def test_connection(self):
        try:
            # Попытка создать сессию и проверить соединение
            session = self.Session()
            result = session.execute(text("SELECT 1"))
            self.assertEqual(result.fetchone()[0], 1, "Database connection failed")
        except Exception as e:
            self.fail(f"Database connection failed: {e}")
        finally:
            session.close()


if __name__ == '__main__':
    unittest.main()


def calculate_commissions(amount, total, rates):
    return {trade_type: rate * (amount if "buy" in trade_type else total) for trade_type, rate in rates.items()}
amount = 1000
total = 5000
rates = {
    "market_buy": 0.001,
    "market_sell": 0.002,
    "limit_buy": 0.0015,
    "limit_sell": 0.0025,
    "stop_limit_buy": 0.002,
    "stop_limit_sell": 0.003
}
print(calculate_commissions(amount,total,rates))


