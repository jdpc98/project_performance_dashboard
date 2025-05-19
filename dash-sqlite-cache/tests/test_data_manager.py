import unittest
from src.data_manager import load_data, cache_data
import sqlite3

class TestDataManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect('data/cache.db')
        cls.cursor = cls.connection.cursor()
        cls.cursor.execute('CREATE TABLE IF NOT EXISTS test_data (id INTEGER PRIMARY KEY, value TEXT)')
        cls.connection.commit()

    @classmethod
    def tearDownClass(cls):
        cls.cursor.execute('DROP TABLE IF EXISTS test_data')
        cls.connection.commit()
        cls.connection.close()

    def test_load_data(self):
        # Arrange
        self.cursor.execute('INSERT INTO test_data (value) VALUES (?)', ('test_value',))
        self.connection.commit()

        # Act
        data = load_data()

        # Assert
        self.assertIn('test_value', data)

    def test_cache_data(self):
        # Arrange
        test_value = 'cache_test_value'

        # Act
        cache_data(test_value)

        # Assert
        self.cursor.execute('SELECT value FROM test_data WHERE value = ?', (test_value,))
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], test_value)

if __name__ == '__main__':
    unittest.main()