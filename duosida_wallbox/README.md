# Duosida Wallbox

Home Assistant add-on for a local LAN Duosida EV wallbox dashboard.

## Features

- Live dashboard over Home Assistant Ingress.
- Polls charger status and configuration over TCP/9988.
- Can change `VendorMaxWorkCurrent`, shown as maximum charging current.

## Requirements

- The Home Assistant host must be able to reach the charger IP.
- The mobile app should not hold the charger connection while this add-on is controlling it.
- Default charger IP is `192.168.7.140`.

## Installation

Copy this repository into the Home Assistant add-ons folder or add it as a local add-on repository, then install the `Duosida Wallbox` add-on.

Configure:

- `charger_host`: charger IP address.
- `poll_interval`: seconds between automatic polling.
- `probe_duration`: seconds to wait for charger responses.

Open the add-on Web UI after starting it.
