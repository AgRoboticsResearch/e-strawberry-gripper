from pymodbus.client import ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.exceptions import ModbusException
from pymodbus.constants import Endian
import time

class GripperControl:
    def __init__(self, port: str, baudrate: int = 115200, raw_max_position: int = 580, raw_min_position: int = 100):
        """
        Initialize the GripperControl class.
        :param port: Serial port (e.g., 'COM9').
        :param baudrate: Baud rate (default is 115200).
        """
        self.port = port
        self.baudrate = baudrate
        self.left_address = 2  # Device address for left gripper
        self.right_address = 10  # Device address for right gripper
        self.pos_register_address = 2  # Position register address
        self.speed_register_address = 3  
        self.pos_pos_lock_register = 8
        self.RAW_MAX_POSITION = raw_max_position # full open
        self.RAW_MIN_POSITION = raw_min_position # full close
        self.PID_P_address = 9
        self.PID_I_address = 10
        self.PID_D_address = 11
        self.client = ModbusSerialClient(port=self.port, baudrate=self.baudrate, timeout=0.005)
        if not self.client.connect():
            raise Exception("Failed to connect to the Modbus device.")
        print(f"GripperControl initialized using port and baudrate: {port}, {baudrate}")

    def close(self):
        """
        关闭 Modbus 客户端连接。
        """
        if self.client:
            self.client.close()
            print("Modbus client connection closed.")

    def _send_modbus_command(self, address: int, register_address: int, value: float) -> bool:
        """Send a Modbus RTU command to the device.
        :return: True if the command was successful, False otherwise.
        """
        flag = False  # Initialize flag as False
               
        try:
            response = self.client.write_register(register_address, value, slave=address)
            if response.isError():
               print(f"Error: {response.message}")
            if response:
                flag = True
            time.sleep(0.001)  # 1 毫秒延迟
                
                
                
        except ModbusException as e:
            print(f"ModbusException occurred while sending command: {e}")
            return False
    
        except Exception as e:
            # print(f"An unexpected error occurred while sending command: {e}")
            return False
        
           
        return flag

    def _read_modbus_register(self, id_address: int, register_address: int, num_registers: int):
        """Read a Modbus register value from the device."""
        
        # try:
        # response = self.client.read_holding_registers(register_address, num_registers, slave=id_address)
        response = self.client.read_holding_registers(register_address, count=num_registers, slave=id_address)
        if response.isError():
            print(f"Read Error: {response}")
            return None
        
        decoder = BinaryPayloadDecoder.fromRegisters(response.registers, byteorder=Endian.BIG)
        return decoder.decode_16bit_uint()
        
        
    
        # except Exception as e:
        #     print(f"An error occurred while reading register: {e}")
        #     return None


    
    def read_position(self, read_num_registers: int = 1):
        """Read the current position of both left and right grippers."""
        
        left_position = self._read_modbus_register(self.left_address, self.pos_register_address, read_num_registers)
        
        right_position = self._read_modbus_register(self.right_address, self.pos_register_address, read_num_registers)
        print("left_position", left_position)
        print("right_position", right_position)
        return left_position, right_position

    def set_pos_lock(self, loc_value: float):
        """Read the current position of both left and right grippers."""
        
        left_pos_lock = self._send_modbus_command(self.left_address, self.pos_pos_lock_register, loc_value)

        right_pos_lock = self._send_modbus_command(self.left_address, self.pos_pos_lock_register, loc_value)
        print("left_pos_lock", left_pos_lock)
        print("right_pos_lock", right_pos_lock)
        return left_pos_lock, right_pos_lock

    def read_pos_lock(self, read_num_registers: int = 1):
        """Read the current position of both left and right grippers."""
        
        left_pos_lock = self._read_modbus_register(self.left_address, self.pos_pos_lock_register, read_num_registers)
        
        right_pos_lock = self._read_modbus_register(self.right_address, self.pos_pos_lock_register, read_num_registers)
        print("left_pos_lock", left_pos_lock)
        print("right_pos_lock", right_pos_lock)
        return left_pos_lock, right_pos_lock

    def set_speed(self, speed: int):
        """
        Set the maximum speed for both left and right grippers.
        :param speed: Target speed value (range 200-1023).
        """
        # Check speed range
        if speed < 200 or speed > 1023:
            print("Error: Speed value must be between 200 and 1023.")
            return

        left_speed = self._send_modbus_command(self.left_address, self.speed_register_address, speed)
        
        right_speed = self._send_modbus_command(self.right_address, self.speed_register_address, speed)
        if left_speed and right_speed:
                print(f"Right gripper speed setting successful: {speed}")
        if left_speed:
            print("left_speed")
        if right_speed:
            print("right_speed")

    
    def map_position(self, percent_position: float):
        """Map the percent position to raw position. 0% to self.RAW_MIN_POSITION, 100% to self.RAW_MAX_POSITION."""
        return int(self.RAW_MIN_POSITION + (self.RAW_MAX_POSITION - self.RAW_MIN_POSITION) * percent_position / 100)


    def set_position_raw(self, close_position: float):
        """Set the position raw value for left and right sides of the driver.
        Retry writing to the right side if the left side is successful.
        """
        # Try writing to the left address first
        write_left_flag = False
        write_left_flag = self._send_modbus_command(self.left_address, self.pos_register_address, int(close_position))
        
        while not write_left_flag:
            write_left_flag = self._send_modbus_command(self.left_address, self.pos_register_address, int(close_position))
        
        # If the left write was successful, start writing to the right
        if write_left_flag:
            print(f"Write to left side successful! Close position: {close_position}")
        else:
            print("set position wrong")
            
            # Keep retrying to write to the right side until it's successful
        write_right_flag = False
        while not write_right_flag:
            write_right_flag = self._send_modbus_command(self.right_address, self.pos_register_address, int(close_position))
            if write_right_flag:
                print(f"Write to right side successful! Close position: {close_position}")
            else:
                print("Retrying write to right side...")
        # else:
        #     print("Failed to write to left side. Retrying...")
        #     # You can implement retry logic here if you want to keep retrying writing to left as well

    def set_position_raw_direct(self, close_position: float):
        """Set the position raw value for left and right sides of the driver.
        Retry writing to the right side if the left side is successful.
        """
        # Try writing to the left address first
        write_left_flag = False
        write_right_flag = False
        write_left_flag = self._send_modbus_command(self.left_address, self.pos_register_address, int(close_position)) ##bad
        
        write_right_flag = self._send_modbus_command(self.right_address, self.pos_register_address, int(close_position))  ##good
        
               
        
        if write_left_flag and write_right_flag:
            print(f"Write to right side successful! Close position: {close_position}")
        


    def set_position_percent(self, percent_position: float):
        """
        Set the gripper position based on a percentage (0-100).
        0% corresponds to RAW_MIN_POSITION (100), 100% corresponds to RAW_MAX_POSITION (580).
        """
        if not 0 <= percent_position <= 100:
            print("Invalid percentage value. Position should be between 0 and 100.")
            return

        # 映射百分比到实际位置
        raw_position = self.map_position(percent_position)
        

        # 设置夹爪位置
        self.set_position_raw_direct(raw_position)
        
        

    def read_PID(self, key, read_num_registers: int = 1):
        if key == "P":
            left_PID_P = self._read_modbus_register(self.left_address, self.PID_P_address, read_num_registers)
            right_PID_P = self._read_modbus_register(self.right_address, self.PID_P_address, read_num_registers)
            print("left_PID_D ", left_PID_P)
            print("right_PID_P: ", right_PID_P)
        elif key == "I":
            left_PID_I = self._read_modbus_register(self.left_address, self.PID_I_address, read_num_registers)
            right_PID_I = self._read_modbus_register(self.right_address, self.PID_I_address, read_num_registers)
            print("left_PID_I: ", left_PID_I)
            print("right_PID_I: ", right_PID_I)
        elif key == "D":
            left_PID_D = self._read_modbus_register(self.left_address, self.PID_I_address, read_num_registers)
            right_PID_D = self._read_modbus_register(self.right_address, self.PID_I_address, read_num_registers)
            print("left_PID_D ", left_PID_D)
            print("right_PID_D: ", right_PID_D)
        else:
            print("The key of PID control is wrong!")
        return True
    

    def set_PID(self, key, value):
        if key == "P":
            left_PID_P = self._send_modbus_command(self.left_address, self.PID_P_address, value)
            right_PID_P = self._send_modbus_command(self.right_address, self.PID_P_address, value)
            print("left_PID_D ", left_PID_P)
            print("right_PID_P: ", right_PID_P)
        elif key == "I":
            left_PID_I = self._send_modbus_command(self.left_address, self.PID_I_address, value)
            right_PID_I = self._send_modbus_command(self.right_address, self.PID_I_address, value)
            print("left_PID_I: ", left_PID_I)
            print("right_PID_I: ", right_PID_I)
        elif key == "D":
            left_PID_D = self._send_modbus_command(self.left_address, self.PID_I_address, value)
            right_PID_D = self._send_modbus_command(self.right_address, self.PID_I_address, value)
            print("left_PID_D ", left_PID_D)
            print("right_PID_D: ", right_PID_D)
        else:
            print("The key of PID control is wrong!")
        return True



