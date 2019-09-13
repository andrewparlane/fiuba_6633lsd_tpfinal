import os

import matplotlib.pyplot as plt

from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Probe.Plot import plot
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Unit import *

import numpy as np

def do_path_test(tech, put):
    # ================================
    # Encontrar la carpeta de liberias
    # ================================
    libraries_path = find_libraries()

    # ====================================
    # Generar el parte general del netlist
    # ====================================
    circuit = Circuit("Gate_Test"+type(put).__name__+"_"+tech.NAME)
    circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"

    vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)     # Fuente de tensión Vdd

    # ===========================
    # La ruta que queremos probar
    # ===========================
    inSources = []
    inSources.append(circuit.V('In', 'In', circuit.gnd, 0))
    put.add_to_circuit(circuit, 'Vdd', 'In', 'Out')

    # Una ruta tiene otras entradas que están puesto en un valor por defecto
    # Por un fuente propio por cada entrada (que no es la entrada 'In')
    # Obtener una lista de estos fuentes
    inSources += put.get_input_sources()

    # muestra el netlist
    print(str(circuit))

    errors = 0
    # 1 entrada  - 2 combinaciones
    # 2 entradas - 4 combinaciones
    # 3 entradas - 8 combinaciones
    # n entradas - 2^n combinaciones
    for inVal in range(2**len(inSources)):
        # bit 0 de inVal corresponde con entrada 0
        # bit 1 de inVal corresponde con entrada 1
        # ...
        # poner los valores correctos en los fuentes de tensión
        inputs = []
        for i in range(len(inSources)):
            nodeInput = 1 if (inVal & (1 << i)) else 0              # esta entrada es un 0 o un 1?
            inputs.append(nodeInput)                                # Guardar una lista de entradas
            inSources[i].dc_value = tech.VDD if nodeInput else 0    # Convertir en una tensión

        expectedOutput = put.get_output_value(inputs)

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
