import os

import matplotlib.pyplot as plt


import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()


from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Probe.Plot import plot
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Unit import *

import numpy as np

import compuertas

libraries_path = find_libraries()
spice_library = SpiceLibrary(libraries_path)

# Compuertas
inv = compuertas.Inversor()

# Netlist
circuit = Circuit('inversor_test')
circuit.include(spice_library['CMOSN'])
circuit.subcircuit(inv)
circuit.V('dd', 'Vdd', circuit.gnd, 5)
vin = circuit.V("In", "In", circuit.gnd, 5)
inv.add_instance(circuit, 1, 'Vdd', "In", "Out", compuertas.W_MIN)

errores = 0
for entrada in range(2):
    vin.dc_value = 0 if entrada == 0 else 5
    esperado = 1 if entrada == 0 else 0

    # Simulación
    simulator = circuit.simulator(temperature=27, nominal_temperature=27)
    analysis = simulator.operating_point()

    salida = float(analysis.out)
    print("Entrada " + str(vin.dc_value) + " V, Salida " + str(salida) + " V")

    if (salida > 4.9):
        logica = 1
    elif (salida < 0.1):
        logica = 0
    else:
        print(str(salida) + " no es un valido")
        continue

    if (logica != esperado):
        print("  Error: " + str(esperado) + " esperado");
        errores += 1

if (errores == 0):
    print("Todos pruebas OK")
