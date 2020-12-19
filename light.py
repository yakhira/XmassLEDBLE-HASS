"""Platform for Xmass LED BLE integration."""
import logging
import re
import pexpect
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)
ST_API_URL = 'https://api.smartthings.com/v1'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional('token'): cv.string,
    vol.Required('devices'): vol.All(cv.ensure_list, [cv.string])
})

def st_connect(token):
    http_adapter = HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 501, 502, 503, 504]
        )
    )

    session = requests.Session()
    session.mount('http://', http_adapter)
    session.mount('https://', http_adapter)
    session.devices = {}
    session.token = token

    if token:
        response = session.get(
            f'{ST_API_URL}/devices',
            headers={
                'Authorization': f'Bearer {token}'
            }
        )
        if response.status_code == 200:
            session.devices = {
                device['label']: device['deviceId']
                for device in response.json()['items']
            }
    return session

def le_scan(bt_names, st_devices, timeout=5):
    devices = []

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

                if name in bt_names:
                    devices.append({
                        'name': name,
                        'address': address,
                        'device_id': st_devices.get(name)
                    })
                else:
                    return devices
    finally:
        scan.sendcontrol('c')
        scan.close()

    return devices

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Xmass LED BLE Light platform."""
    token = config.get('token', '').replace('Bearer ', '')
    st_session = st_connect(token)

    add_entities([
        XmassLEDBLE(bt_device, st_session)
        for bt_device in le_scan(config['devices'], st_session.devices)
    ])

class XmassLEDBLE(LightEntity):
    """Representation of an Xmass LED BLE Light."""

    def __init__(self, bt_device, st_session=None):
        """Initialize an Xmass LED BLE."""
        self._name = bt_device['name']
        self._device = bt_device
        self._st_session = st_session
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
    
    def _get_st_light_state(self):
        if self._device['device_id']:
            response = self._st_session.get(
                f"{ST_API_URL}/devices/{self._device['device_id']}/status",
                headers={
                    'Authorization': f'Bearer {self._st_session.token}'
                }
            )
            if response.status_code == 200:
                for key, value in response.json()['components']['main']['switch'].items():
                    return value.get('value')
        return False
    
    def _set_st_light_state(self, state):
        if self._device['device_id']:
            response = self._st_session.post(
                f"{ST_API_URL}/devices/{self._device['device_id']}/commands",
                headers={
                    'Authorization': f'Bearer {self._st_session.token}'
                },
                json= {
                    'commands': [
                        {
                            'component': 'main',
                            'capability': 'switch',
                            'command': state
                        }
                    ]
                }
            )
            if response.status_code == 200:
                return True
        return False
    
    def _send_bt_command(self, handle, value):
        self._gatt.sendline('connect {0}'.format(self._device['address']))
        self._gatt.expect('Connection successful')
        self._gatt.sendline(f'char-write-cmd {handle} {value}')
        self._gatt.sendline('disconnect')

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self._send_bt_command('0x0000001b', '7eff0401ffffffffef')
        self._set_st_light_state('on')

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._send_bt_command('0x0000001b', '7eff0400ffffffffef')
        self._set_st_light_state('off')

    def update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        st_light_state = self._get_st_light_state()

        if st_light_state == 'on':
            self._send_bt_command('0x0000001b', '7eff0401ffffffffef')
            self._state = True
        elif st_light_state == 'off':
            self._send_bt_command('0x0000001b', '7eff0400ffffffffef')
            self._state = False

        return self._state