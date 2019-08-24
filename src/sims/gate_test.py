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

def do_gate_test(tech, gut):
    # ================================
    # Encontrar la carpeta de liberias
    # ================================
    libraries_path = find_libraries()

    # ====================================
    # Generar el parte general del netlist
    # ====================================
    circuit = Circuit("Gate_Test"+type(gut).__name__+"_"+tech.NAME)
    circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"

    circuit.subcircuit(gut)                                 # Añadir el subcircuito

    vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)     # Fuente de tensión Vdd

    # ================================
    # La compuerta que queremos probar
    # ================================
    inNodes     = []
    inFuentes   = []
    for i in range(gut.get_num_inputs()):
        node = 'in'+str(i)                                      # in0, in1, ...
        inNodes.append(node)                                    # Añadir el nodo a la lista
        inFuentes.append(circuit.V(node, node, circuit.gnd, 0)) # Añadir una fuente de tensión

    gut.add_instance(circuit, 1, 'Vdd', inNodes, "Out", tech.W_MIN)

    # muestra el netlist
    print(str(circuit))

    errors = 0
    # 1 entrada  - 2 combinaciones
    # 2 entradas - 4 combinaciones
    # 3 entradas - 8 combinaciones
    # n entradas - 2^n combinaciones
    for inVal in range(2**gut.get_num_inputs()):
        # bit 0 de inVal corresponde con entrada 0
        # bit 1 de inVal corresponde con entrada 1
        # ...
        # poner los valores correctos en los fuentes de tensión
        inputs = []
        for i in range(gut.get_num_inputs()):
            nodeInput = 1 if (inVal & (1 << i)) else 0              # esta entrada es un 0 o un 1?
            inputs.append(nodeInput)                                # Guardar una lista de entradas
            inFuentes[i].dc_value = tech.VDD if nodeInput else 0    # Convertir en una tensión

        expectedOutput = gut.get_output_value(inputs)

        # Simulación
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.operating_point()

        outputVoltage = float(analysis.out)

        if (outputVoltage > tech.VDD - 0.1):
            actualOutput = 1
        elif (outputVoltage < 0.1):
            actualOutput = 0
        else:
            print(str(outputVoltage) + "V is not a valid logic level")
            errors += 1
            continue

        print("Inputs: " + str(inputs) + " Output: " + str(actualOutput))

        if (actualOutput != expectedOutput):
            print("  Error: " + str(expectedOutput) + " expected");
            errors += 1

    print("Test finished with " + str(errors) + " errors")
