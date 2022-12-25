"""Platform for Xmass LED BLE integration."""
import pexpect
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity

DEFAULT_ADAPTER = 'hci0'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional('adapter', default=DEFAULT_ADAPTER): cv.string,
    vol.Required('name'): cv.string,
    vol.Required('address'): cv.string
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Xmass LED BLE Light platform."""
    add_entities([
        XmassLEDBLE(config)
    ])

class XmassLEDBLE(LightEntity):
    """Representation of an Xmass LED BLE Light."""

    def __init__(self, config):
        """Initialize an Xmass LED BLE."""
        self._adapter = config['adapter']
        self._name = config['name']
        self._address = config['address']
        self._state = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state
    
    def _send_bt_command(self, handle, value):
        return pexpect.run(f"gatttool -i {self._adapter} -b  '{self._address}' --char-write-req -a {handle} -n {value}")

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self._send_bt_command('0x0000001b', '7eff0401ffffffffef')
        self._state = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._send_bt_command('0x0000001b', '7eff0400ffffffffef')
        self._state = False
    
    def update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        return self._state