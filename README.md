# Duosida Wallbox Home Assistant Add-on Repository

Home Assistant Supervisor add-on repository for a Duosida EV wallbox local LAN dashboard.

## Warning / Figyelmeztetes

This repository is under active development and is not an official Duosida or Home Assistant project. It controls EV charger settings over a reverse-engineered local protocol. Use it only if you understand the risks.

No warranty is provided. The author takes no responsibility for damage, malfunction, incorrect charging current, electrical issues, data loss, or any other consequence. Everyone uses this add-on entirely at their own risk.

Ez a repository fejlesztes alatt all, nem hivatalos Duosida vagy Home Assistant projekt. A tolto beallitasait egy visszafejtett lokal protokollon keresztul vezerli. Csak akkor hasznald, ha erted a kockazatokat.

Garancia nincs. A szerzo semmilyen felelosseget nem vall karert, hibas mukodesert, rosszul beallitott toltoaramert, elektromos problemaert, adatvesztesert vagy barmilyen kovetkezmenyert. Mindenki kizarolag sajat felelossegere hasznalja.

## Add-on

- `duosida_wallbox`: web dashboard and local TCP/9988 control for Duosida chargers.

## Installation

1. In Home Assistant, open **Settings -> Add-ons -> Add-on Store**.
2. Open the menu, choose **Repositories**, and add your GitHub repository URL.
3. Install **Duosida Wallbox**.
4. Configure `charger_host`, then start the add-on and open the Web UI.
