# Duosida Wallbox Home Assistant Add-on Repository

Home Assistant Supervisor add-on repository for a Duosida EV wallbox local LAN dashboard.

## Add-on

- `duosida_wallbox`: web dashboard and local TCP/9988 control for Duosida chargers.

## Installation

1. Upload this repository to GitHub.
2. In Home Assistant, open **Settings -> Add-ons -> Add-on Store**.
3. Open the menu, choose **Repositories**, and add your GitHub repository URL.
4. Install **Duosida Wallbox**.
5. Configure `charger_host`, then start the add-on and open the Web UI.

## Development Notes

Only the clean Home Assistant add-on files are intended to be committed. APK reverse-engineering artifacts and local probe/dashboard duplicates are ignored by `.gitignore`.
