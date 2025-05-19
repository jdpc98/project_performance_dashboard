import unittest
from src.database.cache import Cache

class TestCache(unittest.TestCase):

    def setUp(self):
        """Set up a new Cache instance for testing."""
        self.cache = Cache('data/cache.db')

    def test_cache_write_and_read(self):
        """Test writing to and reading from the cache."""
        test_key = 'test_key'
        test_value = {'data': 'test_value'}

        # Write to cache
        self.cache.write(test_key, test_value)

        # Read from cache
        result = self.cache.read(test_key)

        self.assertEqual(result, test_value, "The cached value should match the written value.")

    def test_cache_read_non_existent_key(self):
        """Test reading a non-existent key from the cache."""
        result = self.cache.read('non_existent_key')
        self.assertIsNone(result, "Reading a non-existent key should return None.")

    def tearDown(self):
        """Clean up after each test."""
        self.cache.clear()  # Assuming there's a clear method to reset the cache

if __name__ == '__main__':
    unittest.main()