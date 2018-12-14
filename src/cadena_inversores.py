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

# Nuestros classes en compuertas.py
import compuertas

# ====================
# Parseo de argumentos
# ====================
if (len(sys.argv) != 2):
    print("Please provide number of inverters")
    exit()

num = int(sys.argv[1])
if (num == 0):
    print("can't do 0 inverters")
    exit()

# ================================
# Encontrar la carpeta de liberias
# ================================
libraries_path = find_libraries()
spice_library = SpiceLibrary(libraries_path)

# ========================
# Instancia los compuertas
# ========================
inv = compuertas.Inversor()
#nand = compuertas.Nand()
#nor = compuertas.Nor()

# ==================
# Generar el netlist
# ==================
circuit = Circuit('Cadena de Inversores')   # titulo
circuit.include(spice_library['CMOSN'])     # .include "V35G-spice.lib"
circuit.subcircuit(inv)                     # .subckt inversor .... .ends inversor
circuit.V('dd', 'Vdd', circuit.gnd, 5)      # Fuente de tensión Vdd 5V

# Fuente de tensión de pulses que usamos
# como la entrada de la cadena
circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)

# Los inversores
for i in range(num):
    inNode = 'In' if i == 0 else ('tmp' + str(i))
    outNode = 'Out' if i == (num - 1) else ('tmp' + str(i+1))
    inv.add_instance(circuit, i, 'Vdd', inNode, outNode, compuertas.W_MIN)

# muestra el netlist
print(str(circuit))

# ====================
# Transient Simulación
# ====================
simulator = circuit.simulator(temperature=27, nominal_temperature=27)
analysis = simulator.transient(step_time=10e-15, end_time=1.5e-9)

# ===================
# Parseo de los datos
# para encontrar Tp
# ===================
in_rises = 0
out_transitions = 0

# Puedes acceder cualquier nodo en tu netlist en dos formas:
# analysis['out'] o analysis.out. Unos nombres están keywords
# en SPICE, por ejemplo in. Así no puedes usar analysis.in.
# Puedes usar analysis.in_ pero sugiero que usamos analysis['in']
# para todos los casos.

# analysis['foobar'] es un array de las muestras
# analysis['foobar'].abscissa es un array de los tiempos
# así analysis['foobar'][519] es la muestra del nodo foobar
# al tiempo analysis['foobar'].abscissa[519]

# usamos la función zip() para construir un tuple así que
# podríamos iterar por los dos arrays al mismo tiempo
# v es la tensión del nodo in y t es el tiempo de la muestra
for (v,t) in zip(analysis['in'], analysis['in'].abscissa):
    if (float(v) >= 2.5):
        in_rises = t
        print("In rises past 50% at " + str(in_rises.convert_to_power(-12)))
        break

for (v, t) in zip(analysis['out'], analysis['out'].abscissa):
    # si tenemos un número par de inversores la salida sigue la entrada
    # si tememos un número impar de inversores la salida es el opuesto
    # de la entrada
    if (num % 2):
        # par
        if (float(v) <= 2.5):
            out_transitions = t
            print("Out falls past 50% at " + str(out_transitions.convert_to_power(-12)))
            break
    else:
        # impar
        if (float(v) >= 2.5):
            out_transitions = t
            print("Out rises past 50% at " + str(out_transitions.convert_to_power(-12)))
            break

if (out_transitions == 0):
    print("Out never transititons, increase simulation time")
else:
    tp = out_transitions - in_rises
    print("Tp = " + str(tp.convert_to_power(-12)))

# =================
# Muestra las ondas
# =================
figure = plt.figure(1, (10, 5))
axe = plt.subplot(111)
plt.title('')
plt.xlabel('Time [s]')
plt.ylabel('Voltage [V]')
plt.grid()
plot(analysis['in'], axis=axe)

ledgend = ['In']

for i in range(num - 1):
    node = "tmp" + str(i+1)
    plot(analysis[node], axis=axe)
    ledgend.append(node)

ledgend.append('Out')

plot(analysis.out, axis=axe)
plt.legend(ledgend, loc=(.05,.1))

plt.tight_layout()
plt.show()
