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
from dataclasses import dataclass
from typing import List

@dataclass
class Result:
    tp:         float
    widths:     List[float]

def _get_tp(circuit, tech, put, sim_time, step_time):
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

    # usamos la función zip() para construir un tuple así que
    # podríamos iterar por los dos arrays al mismo tiempo
    # v es la tensión del nodo in y t es el tiempo de la muestra

    # Prhimero encontrar la transición de la entrada
    for (v,t) in zip(analysis['in'], analysis['in'].abscissa):
        if (float(v) >= (tech.VDD / 2)):
            in_rises = t
            #print("In rises past 50% at " + str(in_rises.convert_to_power(-12)))
            break

    # Después encontrar la trasición de la salida
    for (v, t) in zip(analysis['out'], analysis['out'].abscissa):
        # la salida será un flanco ascendente o descendente?
        if (put.inverts()):
            if (float(v) <= (tech.VDD / 2)):
                out_transitions = t
                #print("Out falls past 50% at " + str(out_transitions.convert_to_power(-12)))
                break
        else:
            if (float(v) >= (tech.VDD / 2)):
                out_transitions = t
                #print("Out rises past 50% at " + str(out_transitions.convert_to_power(-12)))
                break

    # =====================
    # Devolver el resultado
    # =====================
    if (out_transitions == 0):
        # La duración de simulación no estuvo suficiente largo
        return -1
    else:
        return float(out_transitions - in_rises)

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
    circuit = Circuit("Monte_Carlo_Sim_"+type(put).__name__+"_"+tech.NAME)
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

    best_result = Result(100.0, put.get_widths())

    ts = time.time();
    for l in range(num_sims):
        if (l % 100 == 0):
            print("Ran " + str(l) + "/" + str(num_sims) + " (" + str((100.0 * l)/num_sims) + "%)")

            tp = _get_tp(circuit, tech, put, sim_time, step_time)

            if (tp < 0):
                # La duración de simulación no estuvo suficiente largo
                # Si vimos una transición antes, entonces es claro que esto no puede ser mejor.
                # Pero si nunca vimos una transición antes, incrementamos la duración
                if (not succesfull_run):
                    sim_time += sim_time_step
                    print("Out never transititons, increasing simulation time to " + str(sim_time))
            else:
                succesfull_run = True

                # Usamos estos anchos si el tiempo de propagación total es menor que el mejor.
                # Nota: que pasa si el tiempo de propagación es 1fs menor que el mejor
                #       pero la area es mucho peor?

                if (tp < best_result.tp):
                    best_result = Result(tp, put.get_widths())
                    # reducir la duración de la simulación a tp + 50ps
                    sim_time    = tp + 50e-12
                    #print("New best Tp: " + str(best_result.tp) + " Widths " + str(best_result.widths) + " total widths: " + str(sum(best_result.widths)) + " reducing simulation time to " + str(sim_time))

        # =====================
        # Actualizar los anchos
        # =====================

        # Usamos los mejores anchos que encontramos y cambiar uno (no el primero)
        widths = best_result.widths

        # Generar un ancho aleatoriamente entre tech.W_MIN y put.get_max_width()
        width = random.uniform(tech.W_MIN, put.get_max_width())

        # Elegir cual ancho cambiar (no elegimos el primero)
        idx = random.randint(1, len(widths)-1)
        widths[idx] = width

        # Hazlo
        put.set_widths(widths)

    # ======================
    # Mostrar los resultados
    # ======================
    te = time.time();
    print("Took " + str(te - ts) + "s to run " + str(num_sims) + " simulations");
    print("Best Tp " + str(best_result.tp) + " Widths " + str(best_result.widths))

    # ====================================
    # Escribir los resultados a un archivo
    # ====================================
    if not os.path.exists("results/"):
        os.mkdir("results/")
    f = open("results/"+type(put).__name__+"_"+tech.NAME+".txt","a+")
    f.write(datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ": Step time " + str(step_time) + " Num sims " + str(num_sims) + " Best Tp " + str(best_result.tp) + " Widths " + str(best_result.widths) + "\n")
    f.close()

    # ================================================
    # Finalmente simula una vez más con anchos mejores
    # Y plotear el resultado
    # ================================================
    if (plot_result):
        put.set_widths(best_result.widths)
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.transient(end_time=sim_time*1.5, step_time=step_time)
        put.plot(analysis, 'In', 'Out')
