# Duosida Wallbox Home Assistant Add-on Repository

Home Assistant Supervisor add-on repository for a Duosida EV wallbox local LAN dashboard.

## Warning / Figyelmeztetes

This repository is under active development and is not an official Duosida or Home Assistant project. It controls EV charger settings over a reverse-engineered local protocol. Use it only if you understand the risks.

No warranty is provided. The author takes no responsibility for damage, malfunction, incorrect charging current, electrical issues, data loss, or any other consequence. Everyone uses this add-on entirely at their own risk.

Ez a repository fejlesztes alatt all, nem hivatalos Duosida vagy Home Assistant projekt. A tolto beallitasait egy visszafejtett lokal protokollon keresztul vezerli. Csak akkor hasznald, ha erted a kockazatokat.

Garancia nincs. A szerzo semmilyen felelosseget nem vall karert, hibas mukodesert, rosszul beallitott toltoaramert, elektromos problemaert, adatvesztesert vagy barmilyen kovetkezmenyert. Mindenki kizarolag sajat felelossegere hasznalja.

## Add-on

- `duosida_wallbox`: web dashboard and local TCP/9988 control for Duosida chargers.

## HACS Integration

This repository also contains a Home Assistant custom integration:

- Domain: `duosida_wallbox`
- HACS type: Integration
- Entities:
  - sensors for status, error code, current, voltage, power, energy, frequency, temperature, transaction id, and charger configuration
  - binary sensors for online, charging, and fault state
  - number entity for maximum charging current
  - switch entity for remote start/stop charging
  - button entity for manual refresh

The integration talks to the add-on HTTP API. Keep the add-on installed and running.

### HACS installation

1. In HACS, open **Integrations**.
2. Open the menu, choose **Custom repositories**.
3. Add this repository URL.
4. Select category **Integration**.
5. Install **Duosida Wallbox**.
6. Restart Home Assistant.
7. Open **Settings -> Devices & services -> Add integration** and search for **Duosida Wallbox**.

### Integration configuration

The setup flow asks for the add-on API URL.

Try the default first:

```text
http://duosida_wallbox:8765
```

If Home Assistant cannot resolve the add-on hostname, expose the add-on network port `8765` in the add-on settings and use:

```text
http://<home-assistant-ip>:8765
```

For remote start, the default ID tag is `HA`.

## Installation

1. In Home Assistant, open **Settings -> Add-ons -> Add-on Store**.
2. Open the menu, choose **Repositories**, and add your GitHub repository URL.
3. Install **Duosida Wallbox**.
4. Configure `charger_host`, then start the add-on and open the Web UI.
