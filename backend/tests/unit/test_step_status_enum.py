"""
Test step status enum values are correctly handled.
"""

import pytest
from app.database.models.chat_message_step import StepStatusEnum


def test_step_status_enum_values():
    """Test that enum values are lowercase strings."""
    assert StepStatusEnum.SUCCESS.value == "success"
    assert StepStatusEnum.ERROR.value == "error"
    assert StepStatusEnum.PENDING.value == "pending"


def test_step_status_enum_string_comparison():
    """Test that enum values can be compared with lowercase strings."""
    assert StepStatusEnum.SUCCESS == "success"
    assert StepStatusEnum.ERROR == "error"
    assert StepStatusEnum.PENDING == "pending"


def test_step_status_enum_from_string():
    """Test that enum can be created from lowercase strings."""
    assert StepStatusEnum("success") == StepStatusEnum.SUCCESS
    assert StepStatusEnum("error") == StepStatusEnum.ERROR
    assert StepStatusEnum("pending") == StepStatusEnum.PENDING


def test_step_status_enum_invalid_value():
    """Test that invalid values raise ValueError."""
    with pytest.raises(ValueError):
        StepStatusEnum("SUCCESS")  # Uppercase should fail
    
    with pytest.raises(ValueError):
        StepStatusEnum("ERROR")  # Uppercase should fail
    
    with pytest.raises(ValueError):
        StepStatusEnum("invalid")  # Invalid value should fail

