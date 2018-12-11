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
nor = compuertas.Nor()

# Netlist
circuit = Circuit('nor_test')
circuit.include(spice_library['CMOSN'])
circuit.subcircuit(nor)
circuit.V('dd', 'Vdd', circuit.gnd, 5)
inA = circuit.V("A", "A", circuit.gnd, 5)
inB = circuit.V("B", "B", circuit.gnd, 5)
nor.add_instance(circuit, 1, 'Vdd', "A", "B", "Out", 2.4e-6)

print(circuit)


errores = 0
for entradaA in range(2):
    inA.dc_value = 0 if entradaA == 0 else 5
    for entradaB in range(2):
        inB.dc_value = 0 if entradaB == 0 else 5

        esperado = 0 if (entradaA == 1 or entradaB == 1) else 1

        # Simulación
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.operating_point()

        salida = float(analysis.out)
        print("A: " + str(inA.dc_value) + " V, B: " + str(inB.dc_value) + " V, Salida " + str(salida) + " V")

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
