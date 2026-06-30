# Duosida Wallbox Home Assistant Integration

HACS custom integration for Duosida EV wallbox local LAN control.

## Warning / Figyelmeztetes

This repository is under active development and is not an official Duosida or Home Assistant project. It controls EV charger settings over a reverse-engineered local protocol. Use it only if you understand the risks.

No warranty is provided. The author takes no responsibility for damage, malfunction, incorrect charging current, electrical issues, data loss, or any other consequence. Everyone uses this integration entirely at their own risk.

Ez a repository fejlesztes alatt all, nem hivatalos Duosida vagy Home Assistant projekt. A tolto beallitasait egy visszafejtett lokal protokollon keresztul vezerli. Csak akkor hasznald, ha erted a kockazatokat.

Garancia nincs. A szerzo semmilyen felelosseget nem vall karert, hibas mukodesert, rosszul beallitott toltoaramert, elektromos problemaert, adatvesztesert vagy barmilyen kovetkezmenyert. Mindenki kizarolag sajat felelossegere hasznalja.

## HACS Integration

- Domain: `duosida_wallbox`
- HACS type: Integration
- Entities:
  - sensors for status, error code, current, voltage, power, energy, frequency, temperature, transaction id, and charger configuration
  - binary sensors for online, charging, and fault state
  - number entity for maximum charging current
  - button entities for manual refresh, remote start, and remote stop

The integration talks directly to the charger on TCP/9988. The add-on is not required for normal Home Assistant use.

### HACS installation

1. In HACS, open **Integrations**.
2. Open the menu, choose **Custom repositories**.
3. Add this repository URL.
4. Select category **Integration**.
5. Install **Duosida Wallbox**.
6. Restart Home Assistant.
7. Open **Settings -> Devices & services -> Add integration** and search for **Duosida Wallbox**.

### Integration configuration

The setup flow asks for:

- `charger_host`: charger IP address, default `192.168.7.140`
- `port`: charger TCP port, default `9988`
- `probe_duration`: seconds to wait for charger responses, default `8`
- `id_tag`: remote start ID tag, default `HA`

The Home Assistant host must be able to reach the charger IP directly. The original mobile app should not hold the charger connection while Home Assistant is polling or controlling it.

## Optional Web Dashboard

The old add-on/web dashboard is not required by the HACS integration. If present locally, it lives under `optional_web_dashboard/`, which is ignored by git.
