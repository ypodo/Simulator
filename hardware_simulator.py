"""
Simulation modules for Bartels Pumps and Ultrasonic Atomization Transducer
These modules simulate the behavior of the hardware components to allow
for software testing before physical hardware is available.
"""

import time
import threading
import random
from enum import Enum
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hardware_sim")

class PumpState(Enum):
    """Enum representing possible states of the Bartels Pump."""
    OFF = 0
    ON = 1
    ERROR = 2

class BartelsPumpSimulator:
    """
    Simulator for Bartels Pump | BP7 with mp-Highdriver4
    
    Specifications:
    - Voltage: 5V
    - Power: 0.5mW
    - Flow Rate: 0-14 ml/min
    - Max Pressure: 500 mbar
    
    mp-Highdriver4 controller features:
    - Frequency control: 25-800 Hz (nominal 100 Hz)
    - Amplitude control: 0-250V
    - Control modes: analog, digital and frequency
    - Supports up to 4 micropumps
    """
    
    def __init__(self, pump_id, initial_volume=100.0, simulate_errors=False):
        """
        Initialize the pump simulator.
        
        Args:
            pump_id: Identifier for this specific pump
            initial_volume: Initial volume of liquid available (ml)
            simulate_errors: Whether to randomly simulate error conditions
        """
        self.pump_id = pump_id
        self.state = PumpState.OFF
        self.flow_rate = 0.0  # ml/min
        self.target_flow_rate = 0.0  # ml/min
        self.volume_remaining = initial_volume  # ml
        self.simulate_errors = simulate_errors
        self.pressure = 0.0  # mbar
        self.running = False
        self.thread = None
        self.total_volume_dispensed = 0.0  # ml
        
        # mp-Highdriver4 specific parameters
        self.frequency = 100  # Hz (default 100 Hz)
        self.amplitude = 0    # 0-100% (scaled from 0-250V)
        self.mode = "frequency"  # "analog", "digital", or "frequency"
        self.fault_status = False
        
        logger.info(f"Pump {pump_id} initialized with {initial_volume}ml")
    
    def start(self):
        """Start the pump at the currently set flow rate."""
        if self.state == PumpState.OFF:
            self.state = PumpState.ON
            self.running = True
            self.thread = threading.Thread(target=self._simulate_running)
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"Pump {self.pump_id} started at {self.flow_rate} ml/min " +
                       f"(freq: {self.frequency} Hz, amp: {self.amplitude}%)")
            return True
        else:
            logger.warning(f"Pump {self.pump_id} already running or in error state")
            return False
    
    def stop(self):
        """Stop the pump."""
        if self.state == PumpState.ON:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1.0)
            self.state = PumpState.OFF
            self.flow_rate = 0.0
            logger.info(f"Pump {self.pump_id} stopped")
            return True
        else:
            logger.warning(f"Pump {self.pump_id} already stopped or in error state")
            return False
    
    def set_flow_rate(self, rate):
        """
        Set the pump flow rate.
        
        Args:
            rate: Flow rate in ml/min (0-14)
            
        Returns:
            bool: Success status
        """
        if rate < 0 or rate > 14:
            logger.error(f"Pump {self.pump_id} - Invalid flow rate: {rate}. Must be between 0-14 ml/min")
            return False
        
        self.target_flow_rate = rate
        
        # Calculate appropriate amplitude based on flow rate (linear approximation)
        # 0 ml/min -> 0% amplitude, 14 ml/min -> 100% amplitude
        self.amplitude = min(100, int((rate / 14.0) * 100))
        
        if self.state == PumpState.ON:
            logger.info(f"Pump {self.pump_id} flow rate changing to {rate} ml/min (amplitude: {self.amplitude}%)")
        else:
            logger.info(f"Pump {self.pump_id} flow rate set to {rate} ml/min (amplitude: {self.amplitude}%, pump not running)")
        return True
    
    def set_frequency(self, frequency):
        """
        Set the operating frequency of the pump driver.
        
        Args:
            frequency: Frequency in Hz (25-800)
            
        Returns:
            bool: Success status
        """
        if frequency < 25 or frequency > 800:
            logger.error(f"Pump {self.pump_id} - Invalid frequency: {frequency}. Must be between 25-800 Hz")
            return False
        
        prev_frequency = self.frequency
        self.frequency = frequency
        
        logger.info(f"Pump {self.pump_id} frequency changed from {prev_frequency} Hz to {frequency} Hz")
        
        # Update flow rate estimation based on frequency change
        # Flow rate is most efficient around 100-150 Hz, falling off at higher and lower frequencies
        # This is a simplified model of the frequency response
        frequency_factor = 1.0
        if frequency < 100:
            # Reduced efficiency below 100 Hz
            frequency_factor = 0.5 + (0.5 * (frequency / 100.0))
        elif frequency > 150:
            # Reduced efficiency above 150 Hz
            frequency_factor = 1.0 - (0.5 * min(1.0, (frequency - 150) / 650.0))
        
        # Adjusted flow rate calculation
        self.target_flow_rate = self.target_flow_rate * (frequency_factor / self._get_frequency_factor(prev_frequency))
        
        logger.info(f"Pump {self.pump_id} flow rate adjusted to {self.target_flow_rate:.2f} ml/min due to frequency change")
        return True
    
    def _get_frequency_factor(self, frequency):
        """Helper to calculate frequency efficiency factor."""
        if frequency < 100:
            return 0.5 + (0.5 * (frequency / 100.0))
        elif frequency > 150:
            return 1.0 - (0.5 * min(1.0, (frequency - 150) / 650.0))
        return 1.0
    
    def set_amplitude(self, amplitude_percent):
        """
        Set the amplitude of the pump driver (percentage of max voltage).
        
        Args:
            amplitude_percent: Amplitude percentage (0-100)
            
        Returns:
            bool: Success status
        """
        if amplitude_percent < 0 or amplitude_percent > 100:
            logger.error(f"Pump {self.pump_id} - Invalid amplitude: {amplitude_percent}. Must be between 0-100%")
            return False
        
        prev_amplitude = self.amplitude
        self.amplitude = amplitude_percent
        
        # Estimate flow rate based on amplitude (simplified linear model)
        self.target_flow_rate = (amplitude_percent / 100.0) * 14.0 * self._get_frequency_factor(self.frequency)
        
        logger.info(f"Pump {self.pump_id} amplitude changed from {prev_amplitude}% to {amplitude_percent}% " +
                   f"(estimated flow rate: {self.target_flow_rate:.2f} ml/min)")
        return True
    
    def set_mode(self, mode):
        """
        Set the operating mode of the pump driver.
        
        Args:
            mode: Operating mode ("analog", "digital", or "frequency")
            
        Returns:
            bool: Success status
        """
        valid_modes = ["analog", "digital", "frequency"]
        if mode not in valid_modes:
            logger.error(f"Pump {self.pump_id} - Invalid mode: {mode}. Must be one of {valid_modes}")
            return False
        
        prev_mode = self.mode
        self.mode = mode
        
        logger.info(f"Pump {self.pump_id} mode changed from {prev_mode} to {mode}")
        return True
    
    def dispense_volume(self, volume, rate=None):
        """
        Dispense a specific volume at the given rate.
        
        Args:
            volume: Volume to dispense in ml
            rate: Flow rate to use (ml/min). If None, use current rate.
            
        Returns:
            bool: Success status
        """
        if volume <= 0:
            logger.error(f"Pump {self.pump_id} - Invalid volume: {volume}. Must be positive")
            return False
            
        if volume > self.volume_remaining:
            logger.error(f"Pump {self.pump_id} - Not enough volume remaining. Requested: {volume}ml, Available: {self.volume_remaining}ml")
            return False
            
        if rate is not None:
            if not self.set_flow_rate(rate):
                return False
        
        # If pump is off, start it
        was_off = (self.state == PumpState.OFF)
        if was_off:
            self.start()
        
        # Calculate time needed for dispensing
        time_needed = (volume / self.target_flow_rate) * 60  # seconds
        
        # Simulate the dispensing by waiting
        logger.info(f"Pump {self.pump_id} dispensing {volume}ml at {self.target_flow_rate} ml/min (will take {time_needed:.1f} seconds)")
        time.sleep(time_needed)
        
        # Update the total dispensed
        self.total_volume_dispensed += volume
        self.volume_remaining -= volume
        
        # If pump was off before, stop it again
        if was_off:
            self.stop()
            
        logger.info(f"Pump {self.pump_id} finished dispensing {volume}ml. Remaining: {self.volume_remaining}ml")
        return True
    
    def refill(self, volume):
        """
        Refill the pump's supply.
        
        Args:
            volume: Volume to add in ml
            
        Returns:
            bool: Success status
        """
        if volume <= 0:
            logger.error(f"Pump {self.pump_id} - Invalid refill volume: {volume}. Must be positive")
            return False
            
        self.volume_remaining += volume
        logger.info(f"Pump {self.pump_id} refilled with {volume}ml. New volume: {self.volume_remaining}ml")
        return True
    
    def get_status(self):
        """
        Get the current status of the pump.
        
        Returns:
            dict: Status information
        """
        return {
            'pump_id': self.pump_id,
            'state': self.state.name,
            'flow_rate': self.flow_rate,
            'target_flow_rate': self.target_flow_rate,
            'volume_remaining': self.volume_remaining,
            'pressure': self.pressure,
            'total_dispensed': self.total_volume_dispensed,
            'frequency': self.frequency,
            'amplitude': self.amplitude,
            'mode': self.mode,
            'fault_status': self.fault_status
        }
    
    def _simulate_running(self):
        """Internal method to simulate the pump running in a separate thread."""
        update_interval = 0.1  # seconds
        last_update = time.time()
        
        while self.running:
            current_time = time.time()
            elapsed = current_time - last_update
            last_update = current_time
            
            # Gradually adjust flow rate toward target
            if self.flow_rate != self.target_flow_rate:
                # Simulate acceleration/deceleration (adjust flow by up to 2 ml/min per second)
                max_change = 2.0 * elapsed
                if self.flow_rate < self.target_flow_rate:
                    self.flow_rate = min(self.target_flow_rate, self.flow_rate + max_change)
                else:
                    self.flow_rate = max(self.target_flow_rate, self.flow_rate - max_change)
            
            # Calculate volume dispensed in this interval
            volume_dispensed = (self.flow_rate / 60.0) * elapsed  # ml
            
            # Update remaining volume
            if volume_dispensed > 0:
                if volume_dispensed <= self.volume_remaining:
                    self.volume_remaining -= volume_dispensed
                    self.total_volume_dispensed += volume_dispensed
                else:
                    # Out of liquid
                    self.total_volume_dispensed += self.volume_remaining
                    self.volume_remaining = 0
                    logger.warning(f"Pump {self.pump_id} ran out of liquid")
                    self.state = PumpState.ERROR
                    self.running = False
                    break
            
            # Simulate random pressure variations
            self.pressure = max(0, min(500, self.pressure + random.uniform(-10, 10)))
            
            # Simulate random errors if enabled
            if self.simulate_errors and random.random() < 0.001:  # 0.1% chance per update
                logger.error(f"Pump {self.pump_id} encountered a simulated random error")
                self.state = PumpState.ERROR
                self.running = False
                break
                
            time.sleep(update_interval)
        
        # Ensure flow rate is 0 when stopped
        if self.state != PumpState.ERROR:
            self.flow_rate = 0.0


class AtomizerState(Enum):
    """Enum representing possible states of the Ultrasonic Atomizer."""
    OFF = 0
    ON = 1
    ERROR = 2


class UltrasonicAtomizerSimulator:
    """
    Simulator for Ultrasonic Atomization Transducer (piezo atomizer)
    
    Specifications:
    - Atomization Rate: 10-30 ml/hour (adjustable)
    - Voltage: 5V DC
    - Power: 1-2W
    - Size: 20mm disc
    - Frequency: 108-120 kHz
    - Droplet Size: 1-5 µm
    """
    
    def __init__(self, atomizer_id="A1", simulate_errors=False):
        """
        Initialize the atomizer simulator.
        
        Args:
            atomizer_id: Identifier for this atomizer
            simulate_errors: Whether to randomly simulate error conditions
        """
        self.atomizer_id = atomizer_id
        self.state = AtomizerState.OFF
        self.frequency = 113.0  # kHz (default)
        self.power_level = 50  # 0-100%
        self.atomization_rate = 15.0  # ml/hour at 50% power
        self.volume_atomized = 0.0  # total ml atomized since reset
        self.simulate_errors = simulate_errors
        self.running = False
        self.thread = None
        self.droplet_size = 3.0  # µm
        self.operation_time = 0.0  # total seconds of operation
        self.last_start_time = None
        
        logger.info(f"Piezo Atomizer {atomizer_id} initialized")
    
    def start(self):
        """Start the atomizer."""
        if self.state == AtomizerState.OFF:
            self.state = AtomizerState.ON
            self.running = True
            self.thread = threading.Thread(target=self._simulate_running)
            self.thread.daemon = True
            self.thread.start()
            self.last_start_time = time.time()
            
            # Simulate startup time
            time.sleep(0.2)
            
            logger.info(f"Atomizer {self.atomizer_id} started at {self.frequency:.1f} kHz, " +
                       f"power level {self.power_level}%")
            return True
        else:
            logger.warning(f"Atomizer {self.atomizer_id} already running or in error state")
            return False
    
    def stop(self):
        """Stop the atomizer."""
        if self.state == AtomizerState.ON:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1.0)
            
            # Update operation time
            if self.last_start_time:
                self.operation_time += time.time() - self.last_start_time
                self.last_start_time = None
                
            self.state = AtomizerState.OFF
            logger.info(f"Atomizer {self.atomizer_id} stopped")
            return True
        else:
            logger.warning(f"Atomizer {self.atomizer_id} already stopped or in error state")
            return False
    
    def set_power_level(self, level):
        """
        Set the power level of the atomizer.
        
        Args:
            level: Power level (0-100%)
            
        Returns:
            bool: Success status
        """
        if level < 0 or level > 100:
            logger.error(f"Atomizer {self.atomizer_id} - Invalid power level: {level}. Must be between 0-100%")
            return False
        
        prev_level = self.power_level
        self.power_level = level
        
        # Update atomization rate based on power level (linear relationship)
        # 0% -> 0 ml/hr, 100% -> 30 ml/hr
        self.atomization_rate = (level / 100.0) * 30.0
        
        # Update droplet size based on power level
        # Higher power tends to decrease droplet size
        self.droplet_size = 5 - (4 * level / 100.0)  # 5-1 µm
        
        logger.info(f"Atomizer {self.atomizer_id} power changed from {prev_level}% to {level}% " +
                   f"(rate: {self.atomization_rate:.1f} ml/hr, droplet size: {self.droplet_size:.1f} µm)")
        return True
    
    def set_frequency(self, frequency):
        """
        Set the operating frequency of the atomizer.
        
        Args:
            frequency: Operating frequency in kHz (108-120)
            
        Returns:
            bool: Success status
        """
        if frequency < 108 or frequency > 120:
            logger.error(f"Atomizer {self.atomizer_id} - Invalid frequency: {frequency}. Must be between 108-120 kHz")
            return False
        
        prev_frequency = self.frequency
        self.frequency = frequency
        
        logger.info(f"Atomizer {self.atomizer_id} frequency changed from {prev_frequency:.1f} kHz to {frequency:.1f} kHz")
        return True
    
    def reset_counters(self):
        """
        Reset the atomizer's volume and time counters.
        
        Returns:
            bool: Success status
        """
        self.volume_atomized = 0.0
        self.operation_time = 0.0
        logger.info(f"Atomizer {self.atomizer_id} counters reset")
        return True
    
    def get_status(self):
        """
        Get the current status of the atomizer.
        
        Returns:
            dict: Status information
        """
        # Update operation time if running
        current_operation_time = self.operation_time
        if self.state == AtomizerState.ON and self.last_start_time:
            current_operation_time += time.time() - self.last_start_time
            
        return {
            'atomizer_id': self.atomizer_id,
            'state': self.state.name,
            'power_level': self.power_level,
            'frequency': self.frequency,
            'atomization_rate': self.atomization_rate,
            'estimated_volume_atomized': self.volume_atomized,
            'droplet_size': self.droplet_size,
            'operation_time': current_operation_time
        }
    
    def _simulate_running(self):
        """Internal method to simulate the atomizer running in a separate thread."""
        update_interval = 0.1  # seconds
        last_update = time.time()
        
        while self.running:
            current_time = time.time()
            elapsed = current_time - last_update
            last_update = current_time
            
            # Calculate volume atomized in this interval
            volume_atomized = (self.atomization_rate / 3600.0) * elapsed  # ml
            
            # Add some randomness to the atomization rate
            volume_atomized *= random.uniform(0.95, 1.05)
            
            # Update total volume atomized
            self.volume_atomized += volume_atomized
            
            # Simulate random errors if enabled
            if self.simulate_errors and random.random() < 0.0005:  # 0.05% chance per update
                logger.error(f"Atomizer {self.atomizer_id} encountered a simulated random error")
                self.state = AtomizerState.ERROR
                self.running = False
                break
                
            time.sleep(update_interval)


class HardwareSimulator:
    """
    Main hardware simulator that manages all simulated devices.
    """
    
    def __init__(self, simulate_errors=False):
        """
        Initialize the hardware simulator.
        
        Args:
            simulate_errors: Whether to randomly simulate error conditions
        """
        self.pumps = {}
        self.atomizers = {}
        self.simulate_errors = simulate_errors
        logger.info("Hardware simulator initialized")
    
    def add_pump(self, pump_id, initial_volume=100.0):
        """
        Add a pump to the simulator.
        
        Args:
            pump_id: Identifier for the pump
            initial_volume: Initial volume in the pump
            
        Returns:
            BartelsPumpSimulator: The created pump simulator
        """
        pump = BartelsPumpSimulator(pump_id, initial_volume, self.simulate_errors)
        self.pumps[pump_id] = pump
        return pump
    
    def add_atomizer(self, atomizer_id="A1", initial_volume=0.0):
        """
        Add an atomizer to the simulator.
        
        Args:
            atomizer_id: Identifier for the atomizer
            initial_volume: Initial volume in the atomizer
            
        Returns:
            UltrasonicAtomizerSimulator: The created atomizer simulator
        """
        atomizer = UltrasonicAtomizerSimulator(atomizer_id, self.simulate_errors)
        self.atomizers[atomizer_id] = atomizer
        return atomizer
    
    def get_pump(self, pump_id):
        """Get a pump by ID."""
        return self.pumps.get(pump_id)
    
    def get_atomizer(self, atomizer_id="A1"):
        """Get an atomizer by ID."""
        return self.atomizers.get(atomizer_id)
    
    def get_all_statuses(self):
        """
        Get status of all simulated devices.
        
        Returns:
            dict: Status information for all devices
        """
        statuses = {
            'pumps': {pump_id: pump.get_status() for pump_id, pump in self.pumps.items()},
            'atomizers': {atomizer_id: atomizer.get_status() for atomizer_id, atomizer in self.atomizers.items()},
            'timestamp': time.time()
        }
        return statuses
    
    def shutdown(self):
        """Shut down all simulated devices."""
        for pump in self.pumps.values():
            if pump.state == PumpState.ON:
                pump.stop()
                
        for atomizer in self.atomizers.values():
            if atomizer.state == AtomizerState.ON:
                atomizer.stop()
                
        logger.info("All hardware devices shut down")


# Example usage
def example_usage():
    """Example showing how to use the simulator."""
    # Create the main simulator
    sim = HardwareSimulator(simulate_errors=False)
    
    # Add 4 pumps
    for i in range(1, 5):
        sim.add_pump(f"P{i}", initial_volume=100.0)
    
    # Add an atomizer
    sim.add_atomizer("A1")
    
    # Use pump 1
    pump1 = sim.get_pump("P1")
    
    # Set frequency and amplitude
    pump1.set_frequency(120)
    pump1.set_amplitude(75)
    
    # Start the pump
    pump1.start()
    
    # Let it run for a while
    time.sleep(3)
    
    # Check status
    print(f"Pump status: {pump1.get_status()}")
    
    # Stop the pump
    pump1.stop()
    
    # Configure and start the atomizer
    atomizer = sim.get_atomizer("A1")
    atomizer.set_frequency(115)
    atomizer.set_power_level(80)
    atomizer.start()
    
    # Let it run for a while
    time.sleep(5)
    
    # Check status
    print(f"Atomizer status: {atomizer.get_status()}")
    
    # Stop the atomizer
    atomizer.stop()
    
    # Shut down everything
    sim.shutdown()


if __name__ == "__main__":
    # Run the example if this file is executed directly
    example_usage()