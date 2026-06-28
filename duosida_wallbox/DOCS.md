# Duosida Wallbox Add-on Documentation

## Options

### `charger_host`

IP address of the charger on the local LAN. Example: `192.168.7.140`.

### `poll_interval`

How often the add-on polls the charger, in seconds.

### `probe_duration`

How long each probe session waits for charger frames, in seconds.

## Troubleshooting

If saving the current fails, close the original mobile app and try again. The charger appears to accept only one active controller reliably.

If the dashboard shows no data but current setting works, the charger did not emit status frames during the probe window. Increase `probe_duration`.
