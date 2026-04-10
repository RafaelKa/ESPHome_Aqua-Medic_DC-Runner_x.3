# ESPHome natively on Aqua Medic DC Runner x.3

**Flash on your own risc, but don't forget to back up the original firmware before flashing.** 

I like the pump much more now ;)

## demo

[![on Youtube](https://img.youtube.com/vi/KLvxjvnuPEE/0.jpg)](https://www.youtube.com/watch?v=KLvxjvnuPEE)

## Current state of project

### What works

* all pump functions
* Wi-Fi status icon on monitor/controller shows the connection status

### plans

* producing and get read of errors in ESPHome:
  * **ER01**: Current consumption too high
  * **ER02**: Temperature too high
  * **ER03**: Pump runs dry
  * **ER04**: Impeller blocked
  * **ER05**: Voltage too high
* enable Wi-Fi AP mode via button on controller like original
  * alternatively WPS
* identify and implement hidden functionality: 
  **issues are welcome**
* try to download / flash the original firmware without unmounting the glued Jebao v1.4 module

## Infos / reverse-engineering

### Hardware
- **Modul:** AI-Thinker ESP-13 (ESP8266EX, 4MB Flash)
- **UART to MCU:** GPIO1 (TXD), GPIO3 (RXD), 9600 bps
- **Programming-pins:** GPIO0 (Flash-Mode), GPIO15 (Boot)
- **power-supply:** 3.3V, GND

#### Jebao v1.4 module

![front](docs/images/Jebao_v1.4.jpeg)

---

![back](docs/images/Jebao_v1.4_back.jpeg)

---

## Protocol Specification: Aqua Medic DC Runner 3.3 (Jebao v1.4 / ESP8266 / ESP-13)

### 1. Physical Layer
*   **Interface:** UART (Serial)
*   **Baudrate:** 9600 bps
*   **Data Bits:** 8
*   **Stop Bits:** 1
*   **Parity:** None
*   **Logic Level:** 3.3V (ESP) / 5V (MCU) via J3Y (S8050) Transistors

---

### 2. Direction: ESP8266 → MCU (Control Commands)

The ESP8266 module sends these packets to the Motor-Mainboard.
**Standard Length:** 14 Bytes (Header + 11 Data + 1 Checksum)


| Byte Index | Function       |  Hex Value  | Description / Examples                          |
|:----------:|:---------------|:-----------:|:------------------------------------------------|
|    0, 1    | **Header**     |   `F5 0A`   | Fixed Start Sequence                            |
|     2      | **Length**     |    `0B`     | 11 Bytes following this byte                    |
|     3      | **Type**       |    `02`     | Command / Control Packet                        |
|     4      | **Power**      | `01` / `00` | **01**: Power ON, **00**: Power OFF             |
|     5      | **Feed**       | `01` / `00` | **01**: Feed/Pause ON, **00**: Normal Mode      |
|     6      | **Speed**      | `1E` - `64` | Power in % (e.g., 1E=30%, 64=100%)              |
|     7      | **Timer**      | `0A` - `3C` | Feed Duration (e.g., 0A=10min, 3C=60min)        |
|     8      | **Mode**       |    `00`     | Operation Mode (00: Constant Flow)              |
|     9      | **Wi-Fi Icon** | `00` - `02` | Display Icon (00: Off, 01: Blinking, 02: Solid) |
|     10     | **Night Mode** |    `1E`     | Night Speed Setting (default 30% / 1E)          |
|   11, 12   | **Reserved**   |   `00 00`   | Unknown / Fixed Padding                         |
|     13     | **Checksum**   |  Variable   | Sum of Bytes 2 through 12 (MOD 256)             |

#### Special Packets (ESP8266 → MCU)

| Packet (Hex)        | Name          | Function                                                       |
|:--------------------|:--------------|:---------------------------------------------------------------|
| `F5 0A 04 03 00 07` | **Init/Wake** | Sent once on boot or hardware reset                            |
| `F5 0A 04 01 00 05` | **Heartbeat** | Sent every 1s to get current state of pump/controller from MCU |

---

### 3. Direction: MCU → ESP8266 (Status Feedback)

The Mainboard mirrors the current state to the Wi-Fi module.
**Standard Length:** 15 Bytes (Header + 12 Data + 1 Checksum)


| Byte Index | Function       |  Hex Value  | Description                             |
|:----------:|:---------------|:-----------:|:----------------------------------------|
|    0, 1    | **Header**     |   `F5 0A`   | Start Sequence                          |
|     2      | **Length**     |    `0C`     | 12 Bytes following                      |
|     3      | **Type**       |    `01`     | Status Update                           |
|     4      | **Power**      | `01` / `00` | Current Power State                     |
|     5      | **Feed**       | `01` / `00` | Current Feed Mode State                 |
|     6      | **Speed**      | `1E` - `64` | Current Speed (from Controller Buttons) |
|     7      | **Timer**      | `0A` - `3C` | Current Timer setting                   |
|   8 - 12   | **Data/Error** |  Variable   | Error codes? (e.g., ER01)               |
|     13     | **Checksum**   |  Variable   | Sum of Bytes 2 through 12               |

---

### 4. Logical Observations
*   **Wattage Display:** The MCU does not seem to measure real current via a shunt; instead, it "maps" the wattage on the display based on the speed percentage (e.g., 100% = 25W).
*   **Checksum Calculation:** Simple 8-bit sum of all bytes starting from Length (Byte 2) up to the byte before the Checksum.
*   **Connectivity:** The Wi-Fi symbol on the controller display is passively controlled by the ESP8266 via Byte 9 in the heartbeat packet.
