# Testing Patterns

**Analysis Date:** 2026-03-14

## Test Framework

**Status:** No testing framework detected

**Not Installed:**
- pytest - No `pytest.ini` or `pyproject.toml` with pytest config
- unittest - No test files present
- No CI/CD testing configuration

**Test Execution:**
```bash
# Testing not currently configured
# To add testing, would recommend:
pytest                 # Run all tests
pytest --cov          # Coverage report
pytest -v             # Verbose output
```

## Test File Organization

**Current State:** No test files present

**Recommended Structure:**
- Location: `tests/` directory at project root
- Naming: `test_*.py` for test files, `*_test.py` alternative
- Structure:
```
tests/
├── __init__.py
├── test_master_scraper.py
├── test_optimize_character.py
├── test_separate_trait_grasta.py
└── fixtures/
    ├── sample_data.csv
    └── mock_html.py
```

## Test Structure

**Code Pattern (Not Yet Implemented):**

Recommended pattern for this codebase:

```python
import pytest
import pandas as pd
from unittest.mock import patch, Mock
from master_scraper import scrape_characters, get_soup, scrape_grasta_general

class TestScraping:
    """Test web scraping functions"""

    def test_get_soup_success(self):
        """Test successful soup retrieval"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '<html></html>'
            mock_get.return_value = mock_response

            soup = get_soup("https://example.com")
            assert soup is not None

    def test_get_soup_failure(self):
        """Test error handling in soup retrieval"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")

            soup = get_soup("https://example.com")
            assert soup is None

    def test_scrape_characters_empty(self):
        """Test character scraping with no results"""
        with patch('master_scraper.get_soup') as mock_soup:
            mock_soup.return_value = None

            result = scrape_characters()
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.fixture
    def sample_character_df(self):
        """Fixture for testing character DataFrame"""
        return pd.DataFrame({
            'name': ['Aldo', 'Riica'],
            'element': ['Fire', 'Water'],
            'weapon': ['Sword', 'Staff'],
            'light_shadow': ['Light', 'Shadow'],
            'personalities': [['Weapon Master'], ['Healer']]
        })
```

## Mocking

**Framework:** unittest.mock (part of Python standard library)

**Patterns:**

For web requests (currently using `requests` library):
```python
from unittest.mock import patch, Mock

with patch('requests.get') as mock_get:
    mock_response = Mock()
    mock_response.text = '<html>...</html>'
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Test code here
```

For BeautifulSoup parsing:
```python
from unittest.mock import patch, Mock

with patch('master_scraper.get_soup') as mock_soup:
    mock_soup.return_value = None  # or Mock BeautifulSoup object

    # Test code here
```

For pandas operations:
```python
import pandas as pd
from pandas.testing import assert_frame_equal

expected_df = pd.DataFrame({...})
actual_df = function_under_test()
assert_frame_equal(expected_df, actual_df)
```

**What to Mock:**
- External network calls (`requests.get`)
- Web parsing results (`BeautifulSoup` objects)
- File I/O operations (except in integration tests)
- Configuration values that vary by environment

**What NOT to Mock:**
- Core pandas operations (DataFrame creation, filtering, concatenation)
- String manipulation and parsing logic
- Local data transformations
- The functions being tested themselves

## Fixtures and Factories

**Test Data (Recommended Pattern):**

```python
import pytest

@pytest.fixture
def sample_character_data():
    """Fixture: Character CSV data as DataFrame"""
    return pd.DataFrame({
        'name': ['Rufus', 'Tsukiha', 'Aldo'],
        'element': ['Lightning', 'Fire', 'Wind'],
        'weapon': ['Greatsword', 'Katana', 'Spear'],
        'light_shadow': ['Light', 'Shadow', 'Light'],
        'personalities': [['Warrior'], ['Samurai'], ['Explorer']]
    })

@pytest.fixture
def sample_grasta_data():
    """Fixture: Grasta CSV data as DataFrame"""
    return pd.DataFrame({
        'name': ['Pain Grasta I', 'HP Up I'],
        'category': ['Attack', 'Life'],
        'tier': ['2', '1'],
        'stats': ['Increases pain damage', 'Increases max HP'],
        'personality_req': ['Warrior', None],
        'is_shareable': [False, True]
    })

@pytest.fixture
def sample_ore_data():
    """Fixture: Ore CSV data as DataFrame"""
    return pd.DataFrame({
        'name': ["Bull's Eye Ore", "Rose with Thorns Ore"],
        'category': ['Ore', 'Ore'],
        'stats': ['Increases crit rate', 'Increases attack and accuracy'],
        'source': ['Dungeon A', 'Dungeon B']
    })
```

**Location:**
- `tests/conftest.py` - Shared fixtures across all test modules
- Module-specific fixtures in same file as tests or in `tests/fixtures/`

## Coverage

**Requirements:** Not currently enforced

**Recommendation:**
- Target 70% statement coverage for critical paths
- 100% coverage for scraping logic (high risk)
- 80%+ for optimization logic (business logic)

**View Coverage:**
```bash
pytest --cov=master_scraper --cov=optimize_character --cov-report=html
# Opens htmlcov/index.html in browser
```

## Test Types

**Unit Tests (Recommended Approach):**
- Scope: Individual functions in isolation
- Example: `test_scrape_characters_returns_dataframe()`
- Mock all external dependencies (network, file I/O)
- Approach: 60-70% of test suite

**Integration Tests (Recommended Approach):**
- Scope: Multiple components working together
- Example: `test_load_data_returns_all_dataframes()` - tests `load_data()` calling `pd.read_csv()`
- Use real CSV files in test fixtures
- Approach: 20-30% of test suite
- Location: `tests/integration/` subdirectory

**E2E Tests (Not Currently Used):**
- Recommended only for critical workflows
- Example: Full pipeline `master_scraper.py` -> `optimize_character.py` with real wiki data
- Would require test data server or mock server
- Not recommended for this codebase (external API dependency)

## Common Patterns

**Async Testing:**
Not applicable - codebase is synchronous

**Error Testing (Recommended Pattern):**

```python
def test_scrape_characters_error_handling():
    """Test that scraper handles network errors gracefully"""
    with patch('master_scraper.get_soup') as mock_soup:
        mock_soup.side_effect = requests.ConnectionError("Network down")

        result = scrape_characters()
        assert isinstance(result, list)
        assert len(result) == 0  # Returns empty list on error

def test_get_meta_build_character_not_found():
    """Test optimization when character doesn't exist"""
    df_c = pd.DataFrame({'name': ['Character1'], 'personalities': [['Trait1']]})
    df_g = pd.DataFrame()
    df_o = pd.DataFrame()

    result = get_meta_build('NonExistent', df_c, df_g, df_o)
    assert isinstance(result, str)
    assert 'Error' in result or 'not found' in result.lower()
```

**DataFrame Assertion Pattern:**

```python
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

def test_scrape_grasta_columns():
    """Test that scraper returns correct DataFrame structure"""
    with patch('master_scraper.get_soup') as mock_soup:
        mock_soup.return_value = Mock()  # Mock soup

        result = scrape_grasta_general("Attack", "http://example.com")

        expected_columns = ['name', 'category', 'tier', 'stats', 'personality_req', 'is_shareable']
        assert list(result.columns) == expected_columns

def test_trait_extraction():
    """Test trait parsing from personalities string"""
    p_str = "['Warrior', 'Weapon Master']"
    traits = ast.literal_eval(p_str)

    assert 'Warrior' in traits
    assert 'Weapon Master' in traits
    assert len(traits) == 2
```

## Configuration

**Test Config (Recommended Setup):**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    scraping: Tests for scraping functions
    optimization: Tests for optimization logic
```

Create `tests/conftest.py`:
```python
import pytest
import os

# Ensure test data is accessible
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

@pytest.fixture(scope='session')
def test_data_dir():
    return TEST_DATA_DIR
```

---

*Testing analysis: 2026-03-14*
