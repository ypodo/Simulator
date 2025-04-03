"""
Examples of controlling multiple Bartels pumps simultaneously
using the hardware simulation modules.
"""

import time
import threading
import logging
from hardware_simulator import HardwareSimulator, PumpState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pump_controller")


class MultiPumpController:
    """
    Controller for managing multiple pumps simultaneously.
    Designed for Bartels Pumps with mp-Highdriver4 controllers.
    """
    
    def __init__(self, num_pumps=4):
        """Initialize the controller with specified number of pumps."""
        self.simulator = HardwareSimulator(simulate_errors=False)
        self.pump_ids = [f"P{i+1}" for i in range(num_pumps)]
        
        # Initialize all pumps
        for pump_id in self.pump_ids:
            self.simulator.add_pump(pump_id, initial_volume=100.0)
        
        # Initialize atomizer
        self.simulator.add_atomizer("A1")
        
        logger.info(f"MultiPumpController initialized with {num_pumps} pumps")
    
    def get_pump(self, pump_id):
        """Get a specific pump by ID."""
        return self.simulator.get_pump(pump_id)
    
    def get_atomizer(self):
        """Get the atomizer."""
        return self.simulator.get_atomizer("A1")
    
    def start_all_pumps(self, flow_rates=None):
        """
        Start all pumps simultaneously, optionally with different flow rates.
        
        Args:
            flow_rates: Optional dictionary mapping pump_id to flow rate.
                        If None, uses the previously set flow rates.
        
        Returns:
            dict: Status of operation for each pump
        """
        results = {}
        
        # Set flow rates if provided
        if flow_rates:
            for pump_id, rate in flow_rates.items():
                if pump_id in self.pump_ids:
                    pump = self.get_pump(pump_id)
                    success = pump.set_flow_rate(rate)
                    logger.info(f"Setting pump {pump_id} flow rate to {rate} ml/min: {'Success' if success else 'Failed'}")
        
        # Start all pumps
        threads = []
        for pump_id in self.pump_ids:
            pump = self.get_pump(pump_id)
            thread = threading.Thread(target=self._start_pump, args=(pump, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        logger.info(f"All pumps started with status: {results}")
        return results
    
    def _start_pump(self, pump, results):
        """Helper method to start a pump in a separate thread."""
        pump_id = pump.pump_id
        success = pump.start()
        results[pump_id] = success
    
    def stop_all_pumps(self):
        """
        Stop all pumps simultaneously.
        
        Returns:
            dict: Status of operation for each pump
        """
        results = {}
        
        # Stop all pumps in parallel
        threads = []
        for pump_id in self.pump_ids:
            pump = self.get_pump(pump_id)
            thread = threading.Thread(target=self._stop_pump, args=(pump, results))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        logger.info(f"All pumps stopped with status: {results}")
        return results
    
    def _stop_pump(self, pump, results):
        """Helper method to stop a pump in a separate thread."""
        pump_id = pump.pump_id
        success = pump.stop()
        results[pump_id] = success
    
    def set_flow_rates(self, rates_dict):
        """
        Set flow rates for multiple pumps.
        
        Args:
            rates_dict: Dictionary mapping pump_id to flow rate
            
        Returns:
            dict: Status of operation for each pump
        """
        results = {}
        
        for pump_id, rate in rates_dict.items():
            if pump_id in self.pump_ids:
                pump = self.get_pump(pump_id)
                results[pump_id] = pump.set_flow_rate(rate)
                
        logger.info(f"Flow rates set with status: {results}")
        return results
    
    def set_pump_parameters(self, pump_id, **params):
        """
        Set multiple parameters for a specific pump.
        
        Args:
            pump_id: Identifier for the pump
            **params: Parameters to set (frequency, amplitude, mode, flow_rate)
            
        Returns:
            dict: Operation success status for each parameter
        """
        pump = self.get_pump(pump_id)
        if not pump:
            logger.error(f"Pump {pump_id} not found")
            return {'success': False, 'error': 'Pump not found'}
        
        results = {'pump_id': pump_id, 'success': True}
        
        if 'frequency' in params:
            success = pump.set_frequency(params['frequency'])
            results['frequency'] = success
            if not success:
                results['success'] = False
                
        if 'amplitude' in params:
            success = pump.set_amplitude(params['amplitude'])
            results['amplitude'] = success
            if not success:
                results['success'] = False
                
        if 'mode' in params:
            success = pump.set_mode(params['mode'])
            results['mode'] = success
            if not success:
                results['success'] = False
                
        if 'flow_rate' in params:
            success = pump.set_flow_rate(params['flow_rate'])
            results['flow_rate'] = success
            if not success:
                results['success'] = False
        
        logger.info(f"Parameters for pump {pump_id} set with status: {results}")
        return results
    
    def dispense_volumes(self, volumes_dict, rates_dict=None):
        """
        Dispense specific volumes from multiple pumps simultaneously.
        
        Args:
            volumes_dict: Dictionary mapping pump_id to volume to dispense
            rates_dict: Optional dictionary mapping pump_id to flow rate
            
        Returns:
            dict: Status of operation for each pump
        """
        results = {}
        
        # Start dispensing in parallel
        threads = []
        for pump_id, volume in volumes_dict.items():
            if pump_id in self.pump_ids:
                pump = self.get_pump(pump_id)
                rate = rates_dict.get(pump_id) if rates_dict else None
                thread = threading.Thread(target=self._dispense_volume, 
                                          args=(pump, volume, rate, results))
                threads.append(thread)
                thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        logger.info(f"All volumes dispensed with status: {results}")
        return results
    
    def _dispense_volume(self, pump, volume, rate, results):
        """Helper method to dispense a volume in a separate thread."""
        pump_id = pump.pump_id
        success = pump.dispense_volume(volume, rate)
        results[pump_id] = success
    
    def get_all_pump_statuses(self):
        """
        Get status of all pumps.
        
        Returns:
            dict: Status information for all pumps
        """
        statuses = {}
        for pump_id in self.pump_ids:
            pump = self.get_pump(pump_id)
            statuses[pump_id] = pump.get_status()
            
        return statuses
    
    def run_synchronized_sequence(self, sequence_steps):
        """
        Run a synchronized sequence of pump operations.
        
        Args:
            sequence_steps: List of dicts, each containing:
                - 'delay': Time to wait before this step (seconds)
                - 'pumps': Dict mapping pump_id to dict with 'action' and parameters
                  Where 'action' can be 'start', 'stop', 'set_flow', 'set_frequency',
                  'set_amplitude', 'set_mode', or 'dispense'
        
        Returns:
            bool: Success status
        """
        for step_num, step in enumerate(sequence_steps, 1):
            # Wait for the specified delay
            if 'delay' in step and step['delay'] > 0:
                logger.info(f"Sequence step {step_num}: Waiting for {step['delay']} seconds")
                time.sleep(step['delay'])
            
            logger.info(f"Executing sequence step {step_num}")
            
            if 'pumps' in step:
                # Group operations by type for parallel execution
                start_ops = {}
                stop_ops = {}
                flow_ops = {}
                dispense_ops = {}
                dispense_rates = {}
                
                # Organize operations by type
                for pump_id, ops in step['pumps'].items():
                    if pump_id not in self.pump_ids:
                        logger.warning(f"Unknown pump ID: {pump_id}")
                        continue
                        
                    action = ops.get('action')
                    if action == 'start':
                        start_ops[pump_id] = True
                    elif action == 'stop':
                        stop_ops[pump_id] = True
                    elif action == 'set_flow':
                        flow_ops[pump_id] = ops.get('rate', 0)
                    elif action == 'set_frequency':
                        pump = self.get_pump(pump_id)
                        if pump:
                            pump.set_frequency(ops.get('frequency', 100))
                    elif action == 'set_amplitude':
                        pump = self.get_pump(pump_id)
                        if pump:
                            pump.set_amplitude(ops.get('amplitude', 50))
                    elif action == 'set_mode':
                        pump = self.get_pump(pump_id)
                        if pump:
                            pump.set_mode(ops.get('mode', 'frequency'))
                    elif action == 'dispense':
                        dispense_ops[pump_id] = ops.get('volume', 0)
                        if 'rate' in ops:
                            dispense_rates[pump_id] = ops['rate']
                
                # Execute operations in parallel by type
                # First set flow rates
                if flow_ops:
                    self.set_flow_rates(flow_ops)
                
                # Then start pumps
                if start_ops:
                    self.start_all_pumps({pid: self.get_pump(pid).target_flow_rate 
                                          for pid in start_ops})
                
                # Then dispense volumes
                if dispense_ops:
                    self.dispense_volumes(dispense_ops, dispense_rates)
                
                # Finally stop pumps
                if stop_ops:
                    for pump_id in stop_ops:
                        self.get_pump(pump_id).stop()
        
        logger.info("Sequence execution completed")
        return True
    
    def control_atomizer(self, action, params=None):
        """
        Control the atomizer (on/off, set frequency, set power).
        
        Args:
            action: String action ('on', 'off', 'set_power', 'set_frequency')
            params: Dictionary of parameters for the action (if needed)
            
        Returns:
            dict: Results of the operation
        """
        atomizer = self.get_atomizer()
        if not atomizer:
            logger.error("Could not find atomizer")
            return {'success': False, 'error': 'Atomizer not found'}
            
        params = params or {}
        result = {'success': False}
        
        if action == 'on':
            result['success'] = atomizer.start()
            
        elif action == 'off':
            result['success'] = atomizer.stop()
            
        elif action == 'set_power':
            if 'level' in params:
                result['success'] = atomizer.set_power_level(params['level'])
            else:
                result['error'] = 'Missing power level parameter'
                
        elif action == 'set_frequency':
            if 'frequency' in params:
                result['success'] = atomizer.set_frequency(params['frequency'])
            else:
                result['error'] = 'Missing frequency parameter'
                
        else:
            result['error'] = f'Unknown atomizer action: {action}'
            
        return result
    
    def shutdown(self):
        """Shutdown all devices."""
        self.simulator.shutdown()
        logger.info("MultiPumpController shut down")


def example_synchronized_pumping():
    """Example of synchronized multi-pump operations."""
    controller = MultiPumpController()
    
    # Example 1: Start all pumps with different flow rates
    print("\n=== Example 1: Starting all pumps with different flow rates ===")
    flow_rates = {
        "P1": 5.0,   # 5 ml/min
        "P2": 8.0,   # 8 ml/min
        "P3": 10.0,  # 10 ml/min
        "P4": 3.0    # 3 ml/min
    }
    controller.start_all_pumps(flow_rates)
    
    # Let them run for a few seconds
    time.sleep(3)
    
    # Check status
    print("\nPump statuses after starting:")
    statuses = controller.get_all_pump_statuses()
    for pump_id, status in statuses.items():
        print(f"{pump_id}: {status['state']}, Flow rate: {status['flow_rate']:.1f} ml/min, " +
              f"Frequency: {status['frequency']} Hz, Amplitude: {status['amplitude']}%")
    
    # Stop all pumps
    controller.stop_all_pumps()
    
    # Example 2: Dispense specific volumes simultaneously
    print("\n=== Example 2: Dispensing specific volumes simultaneously ===")
    volumes = {
        "P1": 2.0,  # 2 ml
        "P2": 3.0,  # 3 ml
        "P3": 1.5,  # 1.5 ml
        "P4": 4.0   # 4 ml
    }
    rates = {
        "P1": 6.0,  # 6 ml/min
        "P2": 9.0,  # 9 ml/min
        "P3": 12.0, # 12 ml/min
        "P4": 7.0   # 7 ml/min
    }
    controller.dispense_volumes(volumes, rates)
    
    # Check status after dispensing
    print("\nPump statuses after dispensing:")
    statuses = controller.get_all_pump_statuses()
    for pump_id, status in statuses.items():
        print(f"{pump_id}: Volume remaining: {status['volume_remaining']:.1f} ml, " +
              f"Total dispensed: {status['total_dispensed']:.1f} ml")
    
    # Example 3: Using mp-Highdriver4 specific settings
    print("\n=== Example 3: Using mp-Highdriver4 specific settings ===")
    
    # Set custom frequency and mode for pump 1
    pump1_params = {
        'frequency': 120,    # 120 Hz
        'amplitude': 80,     # 80% amplitude
        'mode': 'frequency'  # frequency mode
    }
    result = controller.set_pump_parameters("P1", **pump1_params)
    print(f"Set pump 1 parameters: {result}")
    
    # Start the pump
    controller.get_pump("P1").start()
    time.sleep(2)
    
    # Check status
    status = controller.get_pump("P1").get_status()
    print(f"Pump P1 status: {status}")
    
    # Stop the pump
    controller.get_pump("P1").stop()
    
    # Example 4: Run a synchronized sequence with driver-specific parameters
    print("\n=== Example 4: Running a synchronized sequence with driver parameters ===")
    sequence = [
        {
            # Step 1: Set frequencies and start pumps 1 and 2
            'pumps': {
                'P1': {'action': 'set_frequency', 'frequency': 150},
                'P2': {'action': 'set_frequency', 'frequency': 100},
                'P1': {'action': 'start', 'rate': 5.0},
                'P2': {'action': 'start', 'rate': 8.0}
            }
        },
        {
            # Step 2: After 2 seconds, adjust amplitude of pump 1 and start pump 3
            'delay': 2,
            'pumps': {
                'P1': {'action': 'set_amplitude', 'amplitude': 70},
                'P3': {'action': 'set_frequency', 'frequency': 120},
                'P3': {'action': 'start', 'rate': 6.0}
            }
        },
        {
            # Step 3: After 3 more seconds, stop pump 2 and start pump 4 with specific settings
            'delay': 3,
            'pumps': {
                'P2': {'action': 'stop'},
                'P4': {'action': 'set_frequency', 'frequency': 80},
                'P4': {'action': 'set_amplitude', 'amplitude': 60},
                'P4': {'action': 'start'}
            }
        },
        {
            # Step 4: After 2 more seconds, stop all pumps
            'delay': 2,
            'pumps': {
                'P1': {'action': 'stop'},
                'P3': {'action': 'stop'},
                'P4': {'action': 'stop'}
            }
        }
    ]
    controller.run_synchronized_sequence(sequence)
    
    # Example 5: Control atomizer
    print("\n=== Example 5: Control atomizer ===")
    # Set atomizer frequency and power
    controller.control_atomizer('set_frequency', {'frequency': 115.0})
    controller.control_atomizer('set_power', {'level': 75})
    
    # Turn on atomizer
    result = controller.control_atomizer('on')
    print(f"Atomizer turned on: {result}")
    
    # Let it run for 5 seconds
    time.sleep(5)
    
    # Get atomizer status
    atomizer = controller.get_atomizer()
    status = atomizer.get_status()
    print(f"Atomizer status: {status}")
    
    # Turn it off
    result = controller.control_atomizer('off')
    print(f"Atomizer turned off: {result}")
    
    # Shutdown
    controller.shutdown()


if __name__ == "__main__":
    example_synchronized_pumping()