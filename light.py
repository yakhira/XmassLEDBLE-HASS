"""Platform for Xmass LED BLE integration."""
import logging
import re
import pexpect
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('devices'): vol.All(cv.ensure_list, [cv.string])
})

def le_scan(devices, timeout=5):
    found_devices = []

    try:
        scan = pexpect.spawn(
            'hcitool lescan --discovery=l',
            ignore_sighup=False
        )
        scan.expect('nonsense value foobar', timeout=timeout)
    except (pexpect.EOF, pexpect.TIMEOUT):
        for line in scan.before.splitlines():
            match = re.match(r'(([0-9A-Fa-f]{2}:?){6}) (\(?.+\)?)', line.decode())
            if match is not None:
                address = match.group(1)
                name = match.group(3)

                if name in devices or address in devices:
                    found_devices.append({
                        'name': name,
                        'address': address
                    })
    finally:
        scan.sendcontrol('c')
        scan.close()

    return found_devices

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Xmass LED BLE Light platform."""
    add_entities([
        XmassLEDBLE(device)
        for device in le_scan(config['devices'])
    ])

class XmassLEDBLE(LightEntity):
    """Representation of an Xmass LED BLE Light."""

    def __init__(self, device):
        """Initialize an Xmass LED BLE."""
        self._name = device['name']
        self._device = device
        self._state = None

        self._gatt = pexpect.spawn('gatttool -I')

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state
    
    def _send_bt_command(self, handle, value):
        self._gatt.sendline('connect {0}'.format(self._device['address']))
        self._gatt.expect('Connection successful')
        self._gatt.sendline(f'char-write-cmd {handle} {value}')
        self._gatt.sendline('disconnect')

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