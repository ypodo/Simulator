# Hardware Simulation Modules for Raspberry Pi

Simulation modules for Bartels Pumps and Ultrasonic Atomization Transducer. These modules simulate the behavior of hardware components to allow for software testing before physical hardware is available.

## Components Simulated

### Bartels Pump | BP7 with mp-Highdriver4

**Specifications:**
- Voltage: 5V
- Power: 0.5mW
- Flow Rate: 0-14 ml/min
- Max Pressure: 500 mbar
- Units required: 4

**mp-Highdriver4 controller features:**
- Frequency control: 25-800 Hz (nominal 100 Hz)
- Amplitude control: 0-250V
- Control modes: analog, digital and frequency
- Supports up to 4 micropumps

### Ultrasonic Atomization Transducer

**Specifications:**
- Atomization Rate: 10-30 ml/hour
- Voltage: 5V DC
- Power: 1-2W
- Size: 20mm disc
- Frequency: 108-120 kHz
- Droplet Size: 1-5 µm
- Units required: 1

## Features

- Real-time simulation with realistic timing
- Thread-safe operation supporting simultaneous pump control
- Detailed logging of all operations
- Optional simulated errors to test error handling
- Complete status reporting for all devices
- Multiple pump control with synchronized sequences

## Key Files

- `hardware_simulator.py` - Base modules for pump and atomizer simulation
- `multi_pump_controller.py` - Controller for managing multiple pumps simultaneously

## Docker Support

The simulator can be run in a Docker container for easy deployment and testing.

### Building and Running with Docker

```bash
# Build the Docker image
docker build -t pump-simulator .

# Run the container
docker run --name pump-sim pump-simulator

# To run a specific file
docker run --name pump-sim pump-simulator python multi_pump_controller.py
```

### Using Docker Compose

```bash
# Start the simulator
docker-compose up -d

# Execute a command in the running container
docker-compose exec simulator python multi_pump_controller.py

# View logs
docker-compose logs -f

# Stop the simulator
docker-compose down
```

## Python Usage Examples

### Basic Usage Example

```python
from hardware_simulator import HardwareSimulator

# Initialize the simulator
sim = HardwareSimulator()

# Add your devices (4 pumps and 1 atomizer)
for i in range(1, 5):
    sim.add_pump(f"P{i}")
sim.add_atomizer("A1")

# Now use these simulated devices in your control code
pump1 = sim.get_pump("P1")
pump1.set_flow_rate(10)  # ml/min
pump1.start()

atomizer = sim.get_atomizer("A1")
atomizer.set_power_level(50)  # %
atomizer.start()
```

### Advanced MP6-HighDriver4 Features

```python
# Set frequency (25-800 Hz)
pump1.set_frequency(150)

# Set amplitude (0-100%)
pump1.set_amplitude(75)

# Set operating mode
pump1.set_mode("frequency")  # "analog", "digital", or "frequency"
```

### MultiPumpController Example

The MultiPumpController allows controlling all pumps simultaneously:

```python
from multi_pump_controller import MultiPumpController

controller = MultiPumpController()

# Start all pumps with different flow rates
flow_rates = {
    "P1": 5.0,   # 5 ml/min
    "P2": 8.0,   # 8 ml/min
    "P3": 10.0,  # 10 ml/min
    "P4": 3.0    # 3 ml/min
}
controller.start_all_pumps(flow_rates)

# Run a synchronized sequence
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
    # Additional sequence steps...
]
controller.run_synchronized_sequence(sequence)
```