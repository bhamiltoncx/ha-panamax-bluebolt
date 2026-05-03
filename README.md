# Panamax BlueBOLT — Home Assistant Integration

Local-polling integration for Panamax BlueBOLT PDUs (power distribution units).
Communicates over Telnet (port 23) with no authentication required.

## Confirmed Compatible Devices

- Panamax BlueBOLT M4320-PRO (8 outlets)
- Panamax BlueBOLT M4315-PRO (8 outlets, same firmware protocol)

## Features

- **Outlet switches** — turn each outlet on/off individually
- **Voltage sensor** — AC voltage in volts
- **Current sensor** — total current draw in amps
- **Apparent Power sensor** — computed as voltage × current (VA)
- **Fault binary sensors** — Power, Breaker, Wire Fault, Temperature, AVM (diagnostic category)
- **Cycle buttons** — power-cycle each outlet using the device's configured off-duration
- **All On / All Off buttons** — bulk outlet control
- **DHCP auto-discovery** — automatically detected when a Panamax device (MAC OUI `10:65:A3`) joins the network

## Installation (HACS)

1. Add this repository as a custom HACS repository.
2. Install "BlueBolt / Panamax" from the HACS integrations list.
3. Restart Home Assistant.
4. Either accept the discovered device notification or go to **Settings → Integrations → Add Integration → BlueBolt / Panamax**.

## Manual Installation

Copy `custom_components/panamax_bluebolt/` into your HA `config/custom_components/` directory and restart.

## Configuration

| Field | Default | Description |
|---|---|---|
| Host | — | IP address or hostname of the PDU |
| Port | 23 | Telnet port |
| Polling interval | 60 s | How often to query the device (10–3600 s) |

## Known Limitations

- Per-outlet power monitoring is not available from the device protocol; only aggregate voltage and current are exposed.
- Outlet names are fixed as "Outlet 1"–"Outlet 8"; the device does not support named outlets over Telnet.

## Removal

Go to **Settings → Integrations**, find "Panamax BlueBOLT", and click **Delete**.
