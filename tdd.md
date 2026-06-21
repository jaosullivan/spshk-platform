# Guide: Implementing Test-Driven Development (TDD) with Pytest

This guide outlines how to implement **Test-Driven Development (TDD)** using Python and the `pytest` framework. 

---

## 1. Setup and Environment

To get the most out of TDD, you need a test runner that executes automatically whenever you save a file.

### Installation
Install `pytest` along with `pytest-watch` (a file-watching plugin that keeps tests running in the background).

```bash
pip install pytest pytest-watch
```

### Running Tests Automatically
Open a dedicated terminal window and start the file watcher. Leave this running while you code:

```bash
ptw
```
*Every time you save a `.py` file, `pytest` will instantly re-run your entire test suite.*

---

## 2. The Red-Green-Refactor TDD Cycle

TDD follows a strict, rapid loop:

## 3. Step-by-Step TDD Example: Password Validator

We will build a simple password validation utility that checks if a password is at least 8 characters long.

### Loop 1: Check Minimum Length

#### Step 1: RED (Write the Failing Test)
Create your test file first. By convention, `pytest` looks for files starting with `test_`.

```python
# test_validator.py
from validator import is_valid_password

def test_password_too_short_returns_false():
    # Arrange & Act
    result = is_valid_password("short")
    
    # Assert
    assert result is False
```
*Save the file. Your terminal running `ptw` will flash **RED** with a `ModuleNotFoundError` because `validator.py` does not exist yet.*

#### Step 2: GREEN (Write Minimal Code)
Create the application file and write the absolute bare minimum code to make that exact test pass.

```python
# validator.py
def is_valid_password(password: str) -> bool:
    return False  # Hardcoded return value to pass the first test
```
*Save the file. Your terminal will turn **GREEN**. The test passes.*

#### Step 3: REFACTOR
The code is currently just a single line, so there is nothing to clean up yet. Move to the next loop.

---

### Loop 2: Validate a Correct Password

#### Step 1: RED (Add a New Test Case)
Now, add a test case for a password that *should* be valid. This forces us to replace our hardcoded code with real logic.

```python
# test_validator.py
def test_password_long_enough_returns_true():
    assert is_valid_password("secure_password123") is True
```
*Save the file. Your terminal turns **RED**. The first test passes, but our new test fails because the function always returns `False`.*

#### Step 2: GREEN (Write Minimal Code)
Update your application logic just enough to satisfy both tests.

```python
# validator.py
def is_valid_password(password: str) -> bool:
    if len(password) >= 8:
        return True
    return False
```
*Save the file. Your terminal turns **GREEN**. Both tests now pass.*

#### Step 3: REFACTOR (Clean Up)
Look at the production code. We can refactor the `if/else` block into a cleaner, more Pythonic single-line expression.

```python
# validator.py (Refactored)
def is_valid_password(password: str) -> bool:
    return len(password) >= 8
```
*Save the file. Check your terminal. It should remain **GREEN**, proving your refactor did not break the logic.*

---

## 4. Integrating Smoke Tests

While TDD focuses on writing **Unit Tests** for granular logic, **Smoke Tests** are high-level tests used to verify that the critical paths of your application are working after a build or deployment (e.g., "Does the application even boot up?", "Can it reach the database?").

### Categorizing Tests with Pytest Markers
You can use `pytest` markers to separate your rapid TDD unit tests from your smoke tests.

Create a `pytest.ini` file in your root directory to register your custom smoke marker:

```ini
# pytest.ini
[pytest]
markers =
    smoke: Quick, high-level verification tests for deployment or build sanity.
```

### Example Smoke Tests
Create a dedicated smoke test file to verify core system health or crucial end-to-end integration points.

```python
# test_smoke.py
import pytest
import requests
from validator import is_valid_password

@pytest.mark.smoke
def test_application_health_check_endpoint():
    """Smoke Test: Verify the live application API is up and running."""
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.smoke
def test_critical_path_validation_pipeline():
    """Smoke Test: Ensure the system's core validator component executes without crashing."""
    try:
        # A simple sanity check on the validator logic
        output = is_valid_password("any_valid_string_123")
        assert isinstance(output, bool)
    except Exception as e:
        pytest.fail(f"Critical component failed to execute: {e}")
```

### How to Run Your Tests

* **Run only the quick TDD Unit Tests (skipping smoke tests):**
  ```bash
  pytest -m "not smoke"
  ```
* **Run only the Smoke Tests (useful in a deployment/CI pipeline):**
  ```bash
  pytest -m smoke
  ```
* **Run all tests together:**
  ```bash
  pytest
  ```

---

## 5. Pro-Tips for Pytest TDD

* **Organize Projects Cleanly:** Keep your app logic, unit tests, and smoke tests isolated.
  ```text
  ├── src/
  │   └── validator.py
  ├── pytest.ini
  └── tests/
      ├── test_validator.py  (Unit Tests)
      └── test_smoke.py      (Smoke Tests)
  ```
* **Use Descriptive Names:** Give your test functions highly descriptive names starting with `test_` (e.g., `test_password_with_no_numbers_fails`).
* **Isolate Your Code:** Use `pytest-mock` to fake database or external API dependencies during TDD unit testing so your main test loop remains lightning fast. Save the real external connections for your smoke tests.