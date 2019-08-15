import os
from datetime import datetime
import time
import random

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


# ====================
# Parseo de argumentos
# ====================
if (len(sys.argv) != 2):
    print("Please provide step time between 1e-18 and 1e-9")
    exit()

step_time = float(sys.argv[1])
if (step_time < 1e-18 or step_time > 1e-9):
    print("Please provide step time between 1e-18 and 1e-9")
    exit()

# ================================
# Encontrar la carpeta de liberias
# ================================
libraries_path = find_libraries()

# ========================
# Instancia los compuertas
# ========================
inv = tech.Inversor()
#nand = tech.Nand()
#nor = tech.Nor()

# ==================
# Generar el netlist
# ==================
circuit = Circuit('Cadena de Inversores')               # titulo
circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"
circuit.subcircuit(inv)                                 # .subckt inversor .... .ends inversor
vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)     # Fuente de tensión Vdd

# Fuente de tensión de pulses que usamos
# como la entrada de la cadena
vin = circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=tech.VDD, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)

# Los inversores (5)
NUM_INVERSORES = 5
inversores = [];
for i in range(NUM_INVERSORES):
    inNode = 'In' if i == 0 else ('tmp' + str(i))
    outNode = 'Out' if i == (NUM_INVERSORES - 1) else ('tmp' + str(i+1))
    inversores.append(inv.add_instance(circuit, i, 'Vdd', inNode, outNode, tech.W_MIN))

# La carga
carga = circuit.C(1, 'Out', circuit.gnd, 500e-15)

# muestra el netlist
print(str(circuit))

# initialisar el generador alatoria usando el tiempo del sistema
random.seed()

# ====================
# Transient Simulación
# ====================

# start with simulating for 100ps
sim_time = 100e-12
# if simulation times out without seeing the transition, increase sim time by ...
sim_time_step = 100e-12
# Once we've seen a succesfull transisition (sim time was long enough)
# we reduce simulation time to best_tp + 50ps
succesfull_run = False

# mejor tiempo de propagación
best_tp = 100.0

# Netlist y anchos para el mejor tiempo de propagación
best_widths = np.full((NUM_INVERSORES,), tech.W_MIN)

# Falta de memoria después de ~50,000 simulaciones
# Normalmente encontramos el mejor antes de 5,000 simulaciones
NUM_SIMS = 10000;
ts = time.time();
for l in range(NUM_SIMS):
    if (l % 100 == 0):
        print("Ran " + str(l) + "/" + str(NUM_SIMS) + " (" + str((100.0 * l)/NUM_SIMS) + "%)")

    # ======================
    # Ejecutar la simulación
    # ======================
    simulator = circuit.simulator(temperature=27, nominal_temperature=27)
    analysis = simulator.transient(end_time=sim_time, step_time=step_time)

    # ===============
    # Encontrar el Tp
    # ===============
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
        if (float(v) >= (tech.VDD / 2)):
            in_rises = t
            #print("In rises past 50% at " + str(in_rises.convert_to_power(-12)))
            break

    for (v, t) in zip(analysis['out'], analysis['out'].abscissa):
        # si tenemos un número par de inversores la salida sigue la entrada
        # si tememos un número impar de inversores la salida es el opuesto
        # de la entrada
        if (NUM_INVERSORES % 2):
            # par
            if (float(v) <= (tech.VDD / 2)):
                out_transitions = t
                #print("Out falls past 50% at " + str(out_transitions.convert_to_power(-12)))
                break
        else:
            # impar
            if (float(v) >= (tech.VDD / 2)):
                out_transitions = t
                #print("Out rises past 50% at " + str(out_transitions.convert_to_power(-12)))
                break

    # =====================
    # Analizar el resultado
    # =====================

    if (out_transitions == 0):
        # only increase simulation time if we've never seen a valid run
        if (not succesfull_run):
            sim_time += sim_time_step
            print("Out never transititons, increasing simulation time to " + str(sim_time))
    else:
        tp = float(out_transitions - in_rises)
        succesfull_run = True

        if (tp < best_tp):
            best_tp = tp
            for i in range(1, NUM_INVERSORES):
                best_widths[i] = inversores[i].parameters["w"];

            # reduce simulation time to tp + 50ps
            sim_time = tp + 50e-12

            print("New best Tp: " + str(tp) + " reducing simulation time to " + str(sim_time))

        #print("Tp = " + str(tp.convert_to_power(-12)))

    # =====================
    # Actualizar los anchos
    # =====================

    # ---------------------------------------------------------------------
    # Forma 1: cambiamos el ancho de todo los inversores (salvo el primero)
    # ---------------------------------------------------------------------

    #for i in range(1, NUM_INVERSORES):
    #    # Queremos un ancho entre tech.W_MIN y tech.W_MIN + 10e-6
    #    # con intervalos de 0.01e-6. Así generamos un entero entre
    #    # 0 y 1000, multiplicamos por 0.01e-6 y añadimos tech.W_MIN
    #    width = tech.W_MIN + (random.randint(0, 1000) * 0.01e-6);
    #    inversores[i].parameters["w"] = width
    #    #print("testing with width " + str(width));

    # --------------------------------------------------------------------------------
    # Forma 2: Usamos los mejores anchos que encontramos y cambiar uno (no el primero)
    # --------------------------------------------------------------------------------
    for i in range(1, NUM_INVERSORES):
        inversores[i].parameters["w"] = best_widths[i]

    width = tech.W_MIN + (random.randint(0, 2000) * 0.01e-6);
    inversores[random.randint(1,NUM_INVERSORES-1)].parameters["w"] = width


# ======================
# Mostrar los resultados
# ======================

te = time.time();
print("Took " + str(te - ts) + "s to run " + str(NUM_SIMS) + " simulations");
print("Best Tp " + str(best_tp) + " Widths " + str(best_widths))

# ====================================
# Escribir los resultados a un archivo
# ====================================

f = open("cadena_inversores_5_resultados.txt","a+")
f.write(datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ": Step time " + str(step_time) + " Best Tp " + str(best_tp) + " Widths " + str(best_widths) + "\n")
f.close()