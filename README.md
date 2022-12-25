# Xmass LED BLE integration for HomeAssistant

This is an integration for popular Xmass LED RGB lights, currently supports turn on/turn off only.
Optionally available integration with smartthings virtual devices to register your lights in alexa.



### Installation

Copy this folder to `<config_dir>/custom_components/xmassled/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: xmassled
    name: LEDBLE-0387D5 
    address: 78:9C:E7:03:87:D5
```