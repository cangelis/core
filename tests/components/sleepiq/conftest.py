"""Common methods for SleepIQ."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, create_autospec, patch

from asyncsleepiq import (
    SleepIQActuator,
    SleepIQBed,
    SleepIQFoundation,
    SleepIQLight,
    SleepIQPreset,
    SleepIQSleeper,
)
import pytest

from homeassistant.components.sleepiq import DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

BED_ID = "123456"
BED_NAME = "Test Bed"
BED_NAME_LOWER = BED_NAME.lower().replace(" ", "_")
SLEEPER_L_ID = "98765"
SLEEPER_R_ID = "43219"
SLEEPER_L_NAME = "SleeperL"
SLEEPER_R_NAME = "Sleeper R"
SLEEPER_L_NAME_LOWER = SLEEPER_L_NAME.lower().replace(" ", "_")
SLEEPER_R_NAME_LOWER = SLEEPER_R_NAME.lower().replace(" ", "_")
PRESET_L_STATE = "Watch TV"
PRESET_R_STATE = "Flat"

SLEEPIQ_CONFIG = {
    CONF_USERNAME: "user@email.com",
    CONF_PASSWORD: "password",
}


@pytest.fixture
def mock_bed() -> MagicMock:
    """Mock a SleepIQBed object with sleepers and lights."""
    bed = create_autospec(SleepIQBed)
    bed.name = BED_NAME
    bed.id = BED_ID
    bed.mac_addr = "12:34:56:78:AB:CD"
    bed.model = "C10"
    bed.paused = False
    sleeper_l = create_autospec(SleepIQSleeper)
    sleeper_r = create_autospec(SleepIQSleeper)
    bed.sleepers = [sleeper_l, sleeper_r]

    sleeper_l.side = "L"
    sleeper_l.name = SLEEPER_L_NAME
    sleeper_l.in_bed = True
    sleeper_l.sleep_number = 40
    sleeper_l.pressure = 1000
    sleeper_l.sleeper_id = SLEEPER_L_ID

    sleeper_r.side = "R"
    sleeper_r.name = SLEEPER_R_NAME
    sleeper_r.in_bed = False
    sleeper_r.sleep_number = 80
    sleeper_r.pressure = 1400
    sleeper_r.sleeper_id = SLEEPER_R_ID

    bed.foundation = create_autospec(SleepIQFoundation)
    light_1 = create_autospec(SleepIQLight)
    light_1.outlet_id = 1
    light_1.is_on = False
    light_2 = create_autospec(SleepIQLight)
    light_2.outlet_id = 2
    light_2.is_on = False
    bed.foundation.lights = [light_1, light_2]

    return bed


@pytest.fixture
def mock_asyncsleepiq_single_foundation(
    mock_bed: MagicMock,
) -> Generator[MagicMock, None, None]:
    """Mock an AsyncSleepIQ object with a single foundation."""
    with patch("homeassistant.components.sleepiq.AsyncSleepIQ", autospec=True) as mock:
        client = mock.return_value
        client.beds = {BED_ID: mock_bed}

        actuator_h = create_autospec(SleepIQActuator)
        actuator_f = create_autospec(SleepIQActuator)
        mock_bed.foundation.actuators = [actuator_h, actuator_f]

        actuator_h.side = "R"
        actuator_h.side_full = "Right"
        actuator_h.actuator = "H"
        actuator_h.actuator_full = "Head"
        actuator_h.position = 60

        actuator_f.side = None
        actuator_f.actuator = "F"
        actuator_f.actuator_full = "Foot"
        actuator_f.position = 10

        preset = create_autospec(SleepIQPreset)
        mock_bed.foundation.presets = [preset]

        preset.preset = PRESET_R_STATE
        preset.side = None
        preset.side_full = None
        yield client


@pytest.fixture
def mock_asyncsleepiq(mock_bed: MagicMock) -> Generator[MagicMock, None, None]:
    """Mock an AsyncSleepIQ object with a split foundation."""
    with patch("homeassistant.components.sleepiq.AsyncSleepIQ", autospec=True) as mock:
        client = mock.return_value
        client.beds = {BED_ID: mock_bed}

        actuator_h_r = create_autospec(SleepIQActuator)
        actuator_h_l = create_autospec(SleepIQActuator)
        actuator_f = create_autospec(SleepIQActuator)
        mock_bed.foundation.actuators = [actuator_h_r, actuator_h_l, actuator_f]

        actuator_h_r.side = "R"
        actuator_h_r.side_full = "Right"
        actuator_h_r.actuator = "H"
        actuator_h_r.actuator_full = "Head"
        actuator_h_r.position = 60

        actuator_h_l.side = "L"
        actuator_h_l.side_full = "Left"
        actuator_h_l.actuator = "H"
        actuator_h_l.actuator_full = "Head"
        actuator_h_l.position = 50

        actuator_f.side = None
        actuator_f.actuator = "F"
        actuator_f.actuator_full = "Foot"
        actuator_f.position = 10

        preset_l = create_autospec(SleepIQPreset)
        preset_r = create_autospec(SleepIQPreset)
        mock_bed.foundation.presets = [preset_l, preset_r]

        preset_l.preset = PRESET_L_STATE
        preset_l.side = "L"
        preset_l.side_full = "Left"

        preset_r.preset = PRESET_R_STATE
        preset_r.side = "R"
        preset_r.side_full = "Right"

        yield client


async def setup_platform(
    hass: HomeAssistant, platform: str | None = None
) -> MockConfigEntry:
    """Set up the SleepIQ platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=SLEEPIQ_CONFIG,
        unique_id=SLEEPIQ_CONFIG[CONF_USERNAME].lower(),
    )
    mock_entry.add_to_hass(hass)

    if platform:
        with patch("homeassistant.components.sleepiq.PLATFORMS", [platform]):
            assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    return mock_entry
