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

import TSMC180 as tech  # Tecnologia que queremos usar

libraries_path = find_libraries()

# Compuertas
nor = tech.Nor()

# Netlist
circuit = Circuit('nor_test')
circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"
circuit.subcircuit(nor)
circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)
inA = circuit.V("A", "A", circuit.gnd, tech.VDD)
inB = circuit.V("B", "B", circuit.gnd, tech.VDD)
nor.add_instance(circuit, 1, 'Vdd', "A", "B", "Out", tech.W_MIN)

print(circuit)


errores = 0
for entradaA in range(2):
    inA.dc_value = 0 if entradaA == 0 else tech.VDD
    for entradaB in range(2):
        inB.dc_value = 0 if entradaB == 0 else tech.VDD

        esperado = 0 if (entradaA == 1 or entradaB == 1) else 1

        # Simulación
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.operating_point()

        salida = float(analysis.out)
        print("A: " + str(inA.dc_value) + " V, B: " + str(inB.dc_value) + " V, Salida " + str(salida) + " V")

        if (salida > tech.VDD - 0.1):
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
