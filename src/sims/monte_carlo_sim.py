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

# tech          - La tecnologia usar
# put           - Path Under Test (Ruta bajo prueba)
# step_time     - El escalon máximo para usar en la simulación
# num_sims      - El número de simulaciones
#                   Falta de memoria después de ~50,000 simulaciones
#                   Normalmente encontramos el mejor antes de 5,000 simulaciones
# plot_result   - Muestra una grafica de la simulación mejor al final

# Ejemplo:
#   from tech   import TSMC180              as tech     # Tecnologia que queremos usar
#   from paths  import inversor_chain_path  as path     # Path que estamos probando
#   from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo
#
#   put = path.InversorChainPath(tech, 5)
#   mcs.do_monte_carlo_sim(tech, put, 1e-9, 10000, True)

def do_monte_carlo_sim(tech, put, step_time, num_sims, plot_result):
    # ================================
    # Encontrar la carpeta de liberias
    # ================================
    libraries_path = find_libraries()

    # ====================================
    # Generar el parte general del netlist
    # ====================================
    circuit = Circuit('Cadena de Inversores')               # titulo
    circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"

    vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)     # Fuente de tensión Vdd

    # Fuente de tensión de pulses que usamos como la entrada de la ruta
    vin = circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=tech.VDD, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)

    # ===========================
    # La ruta que queremos probar
    # ===========================
    put.add_to_circuit(circuit, 'Vdd', 'In', 'Out')

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
    best_widths = put.get_widths()

    ts = time.time();
    for l in range(num_sims):
        if (l % 100 == 0):
            print("Ran " + str(l) + "/" + str(num_sims) + " (" + str((100.0 * l)/num_sims) + "%)")

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
            # nos interesa cuando la salida tiene un flanco ascendente o descendente?
            if (put.inverts()):
                if (float(v) <= (tech.VDD / 2)):
                    out_transitions = t
                    print("Out falls past 50% at " + str(out_transitions.convert_to_power(-12)))
                    break
            else:
                if (float(v) >= (tech.VDD / 2)):
                    out_transitions = t
                    print("Out rises past 50% at " + str(out_transitions.convert_to_power(-12)))
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
                best_tp     = tp
                best_widths = put.get_widths()

                # reduce simulation time to tp + 50ps
                sim_time    = tp + 50e-12

                print("New best Tp: " + str(tp) + " reducing simulation time to " + str(sim_time))

            #print("Tp = " + str(tp.convert_to_power(-12)))

        # =====================
        # Actualizar los anchos
        # =====================

        # Usamos los mejores anchos que encontramos y cambiar uno (no el primero)
        put.set_widths(best_widths)
        put.change_one_width()

    # ======================
    # Mostrar los resultados
    # ======================
    te = time.time();
    print("Took " + str(te - ts) + "s to run " + str(num_sims) + " simulations");
    print("Best Tp " + str(best_tp) + " Widths " + str(best_widths))

    # ====================================
    # Escribir los resultados a un archivo
    # ====================================
    if not os.path.exists("results/"):
        os.mkdir("results/")
    f = open("results/"+type(put).__name__+"_"+tech.NAME+".txt","a+")
    f.write(datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ": Step time " + str(step_time) + " Num sims " + str(num_sims) + " Best Tp " + str(best_tp) + " Widths " + str(best_widths) + "\n")
    f.close()

    # ================================================
    # Finalmente simula una vez más con anchos mejores
    # Y plotear el resultado
    # ================================================
    if (plot_result):
        put.set_widths(best_widths)
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.transient(end_time=sim_time*1.5, step_time=step_time)
        put.plot(analysis, 'In', 'Out')
