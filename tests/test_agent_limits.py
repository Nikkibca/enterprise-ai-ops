
from app.agents.limits import (
    DEFAULT_MAX_INVESTIGATION_STEPS,
    MAX_INVESTIGATION_STEPS,
    MIN_INVESTIGATION_STEPS,
)


def test_default_max_investigation_steps_is_three():
    assert DEFAULT_MAX_INVESTIGATION_STEPS == 3


def test_minimum_investigation_steps_is_one():
    assert MIN_INVESTIGATION_STEPS == 1


def test_maximum_investigation_steps_is_three():
    assert MAX_INVESTIGATION_STEPS == 3


def test_investigation_step_limit_is_bounded():
    assert (
        MIN_INVESTIGATION_STEPS
        <= DEFAULT_MAX_INVESTIGATION_STEPS
        <= MAX_INVESTIGATION_STEPS
    )

