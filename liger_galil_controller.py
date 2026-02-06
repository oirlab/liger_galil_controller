import argparse
from ipaddress import ip_address
import socket
import time

class GalilDMC:
    def __init__(self, address, port=23, timeout=1):
        self.address = address
        self.port = int(port)
        self.timeout = timeout
        self.sock = None
        self._connect()

    def _connect(self):
        print(f"Connecting to {self.address}:{self.port}...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.address, self.port))
            print("Connected successfully.")

            # Clear any initial banner/garbage from the buffer
            try:
                self.sock.settimeout(0.5)
                initial_data = self.sock.recv(1024)
                if b':' in initial_data:
                    pass
            except socket.timeout:
                pass
            finally:
                self.sock.settimeout(self.timeout)

        except Exception as e:
            print(f"Failed to connect: {e}")
            self._close()
            raise

    def send_command(self, command):
        if not self.sock:
            raise ConnectionError("Not connected to the controller.")

        try:
            cmd_str = command.strip() + '\r'  
            self.sock.sendall(cmd_str.encode('ascii'))
            return self.read_response()

        except socket.error as e:
            print(f"Socket error during send: {e}")
            raise

    def read_response(self):
        data = b''
        try:
            while True:
                chunk = self.sock.recv(1024)
                if not chunk:
                    raise ConnectionError("Connection closed by remote host.")
                
                data += chunk
                if b':' in chunk:
                    break
                    
        except socket.timeout:
            print("Timed out waiting for response.")
            raise

        decoded_response = data.decode('ascii', errors='ignore').strip()
        if decoded_response.endswith(':'):
            decoded_response = decoded_response[:-1].strip()
            
        return decoded_response

    def _close(self):
        if self.sock:
            print("Closing connection...")
            try:
                self.sock.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
            finally:
                self.sock = None
                print("Connection closed.")

def test_stepper_motor(galil: GalilDMC, axis='A', degrees=720, microsteps=1, speed_deg=180, accel_deg=360, active_high=True, smoothing=2):
    """
    Moves the stepper motor a specific number of degrees using Galil best practices.
    
    Args:
        galil (GalilDMC): The connected controller instance.
        axis (str): Axis identifier (e.g., 'A').
        degrees (float): Distance to move in degrees.
        microsteps (int): Microstepping divisor (e.g., 1, 2, 4, 16).
        speed_deg (float): Speed in degrees/sec.
        accel_deg (float): Acceleration in degrees/sec^2.
        active_high (bool): If True, uses MT -2 (Active High). If False, uses MT 2 (Active Low).
        smoothing (int): KS parameter (0.5 to 128). Adds smoothing to step pulses.
    """
    
    # 1. Calculate Counts (Assuming 1.8 degree motor = 200 full steps/rev)
    STEPS_PER_REV_FULL = 200.0
    steps_per_degree = (STEPS_PER_REV_FULL * microsteps) / 360.0
    
    counts = int(degrees * steps_per_degree)
    speed_counts = int(speed_deg * steps_per_degree)
    accel_counts = int(accel_deg * steps_per_degree)

    print(f"--- Move Axis {axis}: {degrees}° ({counts} steps with speed {speed_counts} and accel {accel_counts}) ---")

    # 2. Configure Motor Type (MT)
    # Manual Pg 96: MT 2 = Active Low, MT -2 = Active High 
    mt_value = -2 if active_high else 2
    
    # 3. Setup Sequence
    # ST: Stop any current motion
    # MT: Configure stepper mode
    # KS: Configure stepper smoothing 
    # SH: Servo Here (Energize stepper coils)
    galil.send_command(f'ST {axis};')
    galil.send_command(f'MT{axis}={mt_value};')
    galil.send_command(f'KS{axis}={smoothing};') 
    galil.send_command(f'SH {axis};')

    # 4. Define Motion Profile
    galil.send_command(f'SP{axis}={speed_counts};')
    galil.send_command(f'AC{axis}={accel_counts}')
    galil.send_command(f'DC{axis}={accel_counts}')
    
    # 5. Execute Move
    galil.send_command(f'PR{axis}={counts};')
    galil.send_command(f'BG {axis};')
    
    # 6. Wait for Completion using MC
    galil.send_command(f'MC {axis};')
    
    print(f"Move Complete.")
    print(f"Cycle Complete on Axis {axis}.")

    galil._close()

def disable_stepper_motor(galil: GalilDMC, axis='A'):
    """
    Disables the stepper motor on the specified axis.
    """
    print(f"Disabling stepper motor on axis {axis}...")
    galil.send_command(f'MO {axis};')

    galil._close()

def test_switch(galil: GalilDMC, axis='A'):
    """
    Loops the TS command every second and prints Home, Forward, and Reverse switch status.
    """
    print(f"\n--- Monitoring Axis {axis} Switches (Press Ctrl+C to Stop) ---")
    
    print(f"{'Time':<10} | {'Binary':<10}({'Raw':<2}) | {'Home':<6} {'Fwd Limit':<10} {'Rev Limit':<10}")
    print("-" * 65)

    try:
        while True:
            response = galil.send_command(f'TS {axis}')
            
            try:
                value = int(float(response))
                binary_str = f"{value:08b}"
                
                # Bit 1 = Home (Value 2)
                # Bit 2 = Rev Limit (Value 4)
                # Bit 3 = Fwd Limit (Value 8)
                # Logic: If Bit is 1, input is High (Inactive/Safe). 
                #        If Bit is 0, input is Low (Active/Hit).
                
                is_home_inactive = (value >> 1) & 1
                is_rev_inactive  = (value >> 2) & 1
                is_fwd_inactive  = (value >> 3) & 1

                # home_status = "OFF" if is_home_inactive else "ON"
                # rev_status  = "OK"  if is_rev_inactive  else "HIT"
                # fwd_status  = "OK"  if is_fwd_inactive  else "HIT"

                home_status = "OFF" if is_home_inactive else "ON"
                rev_status  = "OFF"  if is_rev_inactive  else "ON"
                fwd_status  = "OFF"  if is_fwd_inactive  else "ON"

                current_time = time.strftime("%H:%M:%S")
                print(f"{current_time:<10} | {binary_str:<10}({value:<2})  | {home_status:<6} {fwd_status:<10} {rev_status:<10}")
                
            except ValueError:
                print(f"Invalid Response: {response}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n--- Monitoring Stopped ---")

    galil._close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Galil DMC Controller Utility")
    parser.add_argument("-a", "--address", type=ip_address, required=True, help="IP address of the Galil controller")
    parser.add_argument("mode", choices=["switch", "stepper", "disable"], help="Operation mode: switch, stepper, or disable")
    parser.add_argument("axis", choices=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], help="Axis identifier (e.g., A, B, C, D, E, F, G, H)")
    args = parser.parse_args()
    
    address = args.address
    port = 23
    galil = GalilDMC(str(address), port)

    try:
        if args.mode == "switch":
            test_switch(galil, axis=args.axis)
        elif args.mode == "stepper":
            test_stepper_motor(galil, axis=args.axis)
        elif args.mode == "disable":
            disable_stepper_motor(galil, axis=args.axis)

    except Exception as e:
        print(f"An error occurred: {e}")