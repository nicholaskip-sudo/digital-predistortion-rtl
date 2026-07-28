# UVM Verification Architecture


dpd_short_uvm_test / dpd_full_uvm_test
└── dpd_env
    ├── dpd_agent
    │   ├── dpd_sequencer
    │   ├── dpd_driver
    │   └── dpd_output_monitor
    ├── dpd_scoreboard
    └── dpd_functional_coverage

## Sequence and driver

The sequence reads the Python-generated input files and creates one transaction per
complex sample. The driver asserts the transaction on a falling edge and retires it
only after observing the actual rising-edge 'in_valid && in_ready' transfer.

The driver also applies deterministic output backpressure.

## Monitor and scoreboard

The output monitor publishes every accepted output. The scoreboard compares each I/Q
pair against the Python-generated expected files using exact four-state comparisons.

## Functional coverage

The coverage component samples the interface directly at rising edges. It observes
accepted data, protocol states, backpressure, saturation, and stall runs without
altering the monitor or scoreboard transaction paths.
