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
inv = tech.Inversor()

# Netlist
circuit = Circuit('inversor_test')
circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"
circuit.subcircuit(inv)
circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)
vin = circuit.V("In", "In", circuit.gnd, tech.VDD)
inv.add_instance(circuit, 1, 'Vdd', "In", "Out", tech.W_MIN)

errores = 0
for entrada in range(2):
    vin.dc_value = 0 if entrada == 0 else tech.VDD
    esperado = 1 if entrada == 0 else 0

    # Simulación
    simulator = circuit.simulator(temperature=27, nominal_temperature=27)
    analysis = simulator.operating_point()

    salida = float(analysis.out)
    print("Entrada " + str(vin.dc_value) + " V, Salida " + str(salida) + " V")

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
