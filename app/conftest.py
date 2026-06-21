import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def no_celery_dispatch():
    """Prevent Celery tasks from trying to connect to Redis during tests."""
    with patch('members.tasks.generate_member_qr_task.delay'):
        yield
