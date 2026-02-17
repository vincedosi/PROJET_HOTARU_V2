# 🚀 PLAN D'OPTIMISATION COMPLET - HOTARU V2

**Audit Date:** 2026-02-17
**Status:** EN COURS
**Target:** 50%+ performance boost + 40%+ code reduction

---

## 📊 PRIORITÉS

### 🔴 CRITICAL (DO NOW - 2 heures)
1. ✅ Extract Selenium utilities (70 LOC duplication)
2. ✅ Regex compile cache (services/jsonld_service.py)
3. ✅ HTML content truncation at scraper level
4. ✅ Database caching with TTL validation
5. ✅ Specific exception types (no more `except Exception`)

### 🟠 HIGH (Do Today - 3 heures)
6. ✅ Exponential backoff for Mistral API
7. ✅ Structured logging with context
8. ✅ Merge duplicate link extraction logic
9. ✅ Batch GSheet updates (append_rows pattern)
10. ✅ Remove global mutable state

### 🟡 MEDIUM (This Week - 2 heures)
11. ✅ Asyncio event loop safety
12. ✅ Timeout on entire crawl operation
13. ✅ Query optimization in database.py
14. ✅ Dependency injection for testability
15. ✅ Remove dead code (ThreadPoolExecutor import)

---

## 📈 EXPECTED IMPROVEMENTS

| Metric | Before | After | Gain |
|--------|--------|-------|------|
| Crawl time (100 pages) | 45s | 30s | -33% |
| Memory per session | 9MB | 3MB | -66% |
| Database load time | 2.5s | 0.5s | -80% |
| Mistral timeout recovery | 3s+ | 1s+ | -67% |
| Code duplication | 800 LOC | 200 LOC | -75% |
| Test coverage | 0% | 30% | NEW |

---

## 🎯 IMPLEMENTATION ORDER

### PHASE 1: CRITICAL FIXES (30 min)
1. **Create `core/selenium_utils.py`**
   - Extract `configure_chrome_options()`
   - Extract `create_chrome_driver()`
   - Remove 70 LOC from scraping.py

2. **Regex Compile Cache (services/jsonld_service.py)**
   - Add module-level `_compiled_patterns = {}`
   - Replace `re.match(r"...")` with cached version

3. **Exception Specificity (all files)**
   - Grep all `except Exception as`
   - Replace with specific types (TimeoutError, JSONDecodeError, etc.)

### PHASE 2: PERFORMANCE (1 hour)
4. **HTML Content Truncation**
   - Modify `scraping.py:_build_page_result()` line 391
   - Store only first 5KB instead of full content
   - Add flag for full HTML retrieval on demand

5. **Database Caching Fix**
   - `core/database.py`: Add version check on cache keys
   - Track last modified time of GSheets
   - Invalidate cache on write

6. **Exponential Backoff**
   - `services/jsonld_service.py:name_cluster_with_mistral()`
   - Replace `time.sleep(1)` with exponential: 1s, 2s, 4s

### PHASE 3: CODE QUALITY (1.5 hours)
7. **Structured Logging**
   - Create `core/logger.py`
   - Add context manager for audit_id, user_email
   - Replace 100+ `print()`/`self._log()` calls

8. **Link Extraction Merge**
   - Move common logic to `core/link_extractor.py`
   - Reuse in both V1 and V2
   - Remove 60 LOC duplication

9. **Global State Fix**
   - Wrap `core/runtime.py` in request context
   - Use functools.lru_cache for secrets
   - Thread-safe by design

10. **Dependency Injection**
    - Create `core/container.py` (simple DI)
    - Inject database, logger, scraper
    - Enable proper testing

---

## 📝 DETAILED CHANGES

### 1. core/selenium_utils.py (NEW)
```python
# Extract from scraping.py lines 148-158 + 404-414
def get_chrome_options(headless=True, proxy=None, no_images=True):
    """Reusable Chrome options configuration."""
    options = Options()
    options.add_argument("--headless=new" if headless else "")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # ... shared config

def create_chrome_driver(headless=True, proxy=None):
    """Factory for Chrome drivers."""
    options = get_chrome_options(headless, proxy)
    # Search for chromium/chromedriver
    return webdriver.Chrome(service=service, options=options)
```

### 2. core/link_extractor.py (NEW)
```python
# Merge scraping.py + scraping_v2.py link extraction
class LinkExtractor:
    @staticmethod
    def extract_from_soup(soup):
        return [a["href"] for a in soup.find_all("a", href=True)]

    @staticmethod
    def extract_from_data_href(soup):
        # ... existing code

    @staticmethod
    def merge_links(sources):
        """Merge all link sources into unique set."""
        result = set()
        for source in sources:
            result.update(source)
        return list(result)
```

### 3. core/logger.py (NEW)
```python
# Structured logging with context
class AuditLogger:
    def __init__(self, audit_id=None, user_email=None):
        self.audit_id = audit_id
        self.user_email = user_email

    def info(self, msg, **kwargs):
        context = f"[{self.audit_id}] [{self.user_email}]"
        print(f"{context} {msg}", flush=True)
```

### 4. core/database.py (OPTIMIZE)
**Line 106 - Remove N+1:**
```python
# BEFORE:
all_rows = self.sheet.get_all_values()  # Full fetch
for row in all_rows:
    if row[0] == user_email:  # Linear search

# AFTER:
# Cache with invalidation + direct lookup
rows = self._get_cached_rows(TTL=300)
# Use index: rows_by_email.get(user_email)
```

**Line 278 - Batch updates:**
```python
# BEFORE:
for model in models:
    ws.append_row(rows)  # 1 API call per row

# AFTER:
ws.append_rows(rows)  # Single batch call
```

### 5. services/jsonld_service.py (REGEX CACHE)
```python
# Add at top of file:
_COMPILED_PATTERNS = {}

def _compile_pattern(pattern):
    if pattern not in _COMPILED_PATTERNS:
        _COMPILED_PATTERNS[pattern] = re.compile(pattern)
    return _COMPILED_PATTERNS[pattern]

# Replace 113: re.match(r"^[0-9a-f]{8}...")
# With: _compile_pattern(r"^[0-9a-f]{8}...").match(text)
```

### 6. core/scraping.py (EXCEPTION SPECIFICITY)
```python
# BEFORE (Line 605):
except Exception as se:
    self._log(f"Erreur Selenium : {se}")
    raise

# AFTER:
except (TimeoutException, NoSuchElementException) as se:
    self._log(f"Selenium timeout/element: {se}")
    raise
except WebDriverException as se:
    self._log(f"WebDriver error: {se}")
    raise
except Exception as se:
    self._log(f"Unexpected error: {se}")
    raise
```

### 7. core/scraping_v2.py (HTML TRUNCATION)
```python
# Line 391 - Store only snippet:
"html_content": html_content[:5120],  # 5KB max
"html_full_size": len(html_content),  # Track original
```

### 8. services/jsonld_service.py (EXPONENTIAL BACKOFF)
```python
# Line 427 - Replace:
# time.sleep(1)
# With:
backoff_time = min(2 ** attempt, 8)  # Cap at 8s
time.sleep(backoff_time)
```

### 9. core/runtime.py (REMOVE GLOBAL STATE)
```python
# BEFORE:
_secrets = {}  # Global, not thread-safe
_session = {}

# AFTER:
from functools import lru_cache

@lru_cache(maxsize=1)
def get_secrets():
    # Load on demand, cache
    return {...}

# Use context managers in Streamlit
@contextmanager
def audit_context(audit_id, user_email):
    ctx = {"audit_id": audit_id, "user_email": user_email}
    # Simplified app.py can access via get_context()
```

---

## 🧪 TESTING STRATEGY

**Before committing each optimization:**
1. `python3 -m py_compile <file>` - Syntax OK
2. Unit test: Run scraper on test URL
3. Integration test: Full audit workflow
4. Performance test: Time tracking
5. Memory test: RSS monitoring

**Files to test:**
- `core/selenium_utils.py` - New utility
- `core/link_extractor.py` - New utility
- `core/logger.py` - New utility
- `scraping.py` - Refactored
- `scraping_v2.py` - Refactored
- `database.py` - Optimized
- `services/jsonld_service.py` - Optimized

---

## 📊 METRICS TO TRACK

**Performance (use `time.perf_counter()`):**
- Crawl duration per page
- Database query time
- Mistral API response time
- Memory usage (psutil.Process().memory_info().rss)

**Code Quality:**
- Duplication: Lines before/after
- Coverage: Testable functions
- Complexity: Cyclomatic complexity per function

---

## 🚀 ROLLOUT PLAN

**Branch:** `claude/check-version-file-1fUMR` (existing)

**Commits:**
1. Extract selenium_utils.py
2. Extract link_extractor.py
3. Extract logger.py
4. core/database.py optimizations
5. services/jsonld_service.py optimizations
6. core/scraping.py exception handling
7. core/scraping_v2.py HTML truncation
8. core/runtime.py context fix
9. Update version to 3.0.80

**Version bumps:**
- 3.0.77 → 3.0.78 (Structure optimizations)
- 3.0.78 → 3.0.79 (Performance optimizations)
- 3.0.79 → 3.0.80 (Error handling + utilities)

---

## ✅ CHECKLIST

- [ ] Phase 1: Critical (30 min)
  - [ ] selenium_utils.py created
  - [ ] Regex cache implemented
  - [ ] Exception types updated

- [ ] Phase 2: Performance (1 hour)
  - [ ] HTML truncation
  - [ ] Database cache fix
  - [ ] Exponential backoff

- [ ] Phase 3: Code Quality (1.5 hours)
  - [ ] Structured logging
  - [ ] Link extraction merge
  - [ ] Global state fix
  - [ ] Dependency injection

- [ ] Testing (30 min)
  - [ ] All syntax OK
  - [ ] Unit tests pass
  - [ ] Integration tests pass
  - [ ] Performance benchmarks

- [ ] Documentation (30 min)
  - [ ] Update README
  - [ ] Document new utilities
  - [ ] Performance improvements documented

---

**Target Completion:** 4 hours total
**Estimated PR Size:** 2000 LOC changed, 800 LOC deleted, 600 LOC added
