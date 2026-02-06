# liger_galil_controller

Galil Motion Controller (DMC-4080) utility for Liger (WMKO). This script allows for testing switches, moving stepper motors, and disabling stepper motors using a Galil controller.

## Requirements

- Python 3 (3.13)
- Network connectivity to the Galil controller

## Usage

```bash
python3 liger_galil_controller.py [-h] -a ADDRESS {switch,stepper,disable} {A,B,C,D,E,F,G,H}
```

### Arguments

- `-a ADDRESS`, `--address ADDRESS`: IP address of the Galil controller (Required)
- `mode`: Operation mode. Choices:
    - `switch`: Monitor switch status (Home, Forward Limit, Reverse Limit)
    - `stepper`: Move the stepper motor with pre-configured parameters
    - `disable`: Disable the stepper motor on the specified axis
- `axis`: Axis identifier. Choices: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`

### Examples

#### Monitor Switches
Monitor the status of switches on Axis A. Press `Ctrl+C` to stop.
```bash
python3 liger_galil_controller.py -a 192.168.1.10 switch A
```

#### Move Stepper Motor
Move the stepper motor on Axis B. The movement parameters (degrees, speed, acceleration) are currently configured in the code.

> [!WARNING]
> You must disable the stepper motor after running the stepper command. The stepper motor will become extremely hot due to the current continuing to flow to the motor.
```bash
python3 liger_galil_controller.py -a 192.168.1.10 stepper B
```

#### Disable Stepper Motor
Disable the stepper motor on Axis B.
```bash
python3 liger_galil_controller.py -a 192.168.1.10 disable B
```
