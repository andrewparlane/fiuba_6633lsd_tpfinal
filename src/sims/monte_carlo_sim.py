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
    totalWidth: float

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
    # initialisar el generador alatoria usando el tiempo del sistema
    random.seed()

    print("Running with step_time " + str(step_time) + ", num_sims " + str(num_sims))

    # ==================
    # Generar el netlist
    # ==================
    libraries_path = find_libraries()
    circuit = Circuit("Monte_Carlo_Sim_"+type(put).__name__+"_"+tech.NAME)
    circuit.include(libraries_path + "/" + tech.LIB_NAME)   #.inclcude "foo.lib"

    vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)     # Fuente de tensión Vdd

    # Fuente de tensión de pulses que usamos como la entrada de la ruta
    vin = circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=tech.VDD, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)

    # La ruta que queremos probar
    put.add_to_circuit(circuit, 'Vdd', 'In', 'Out')

    # ======================
    # Hacer las simulaciones
    # ======================

    # Comienza simulando por 100ps
    sim_time = 100e-12

    ts = time.time();

    # if simulation times out without seeing the transition, increase sim time by ...
    sim_time_step = 100e-12
    # Once we've seen a succesfull transisition (sim time was long enough)
    # we reduce simulation time to best_tp + 50ps
    succesfull_run = False

    # Hay varios resultados con el mismo (o muy parecido) Tp
    # Si una simulación da un Tp un poco peor (1%?) peor usa menos area, deberíamos
    # usar esto resultado cómo el mejor.
    TP_FLEX_PERCENT = 1.0

    # Guardamos el mejor Tp encontrado (comenzamos con 100s, así que cualquier simulación va a mejorar)
    best_tp = 100.0

    # Y guardamos el resultado actual (tal vez no el mejor Tp, pero el mejor area y muy cerca el mejor Tp)
    result = Result(best_tp, put.get_widths(), sum(put.get_widths()))

    for l in range(num_sims):
        if (l % 100 == 0):
            print("Ran " + str(l) + "/" + str(num_sims) + " (" + str((100.0 * l)/num_sims) + "%)")

        widths = put.get_widths()
        totalWidth = sum(widths)

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

            print("tp: " + str(tp) + ", widths: " + str(widths) + ", totalWidth: " + str(totalWidth))

            # este resultado tiene menor tp que el corriente mejor?
            if (tp < best_tp):
                print("  New Best Tp")
                best_tp = tp

                # reducir la duración de la simulación a tp + 50ps
                sim_time = tp + 50e-12

                # Tenemos un nuevo mejor Tp. Solo actualizamos el mejor resultado si tiene un Tp
                # más lento (más de TP_FLEX_PERCENT) de este resultado. O si esta simulación también
                # tiene mejor area que el mejor resultado.

                if ((result.tp > (best_tp * ((100 + TP_FLEX_PERCENT) / 100))) or
                    (result.totalWidth > totalWidth)):
                    print("  New best result")
                    result = Result(tp, widths, totalWidth)
            else:

                # Aunque este resultado no tiene el mejor Tp, si es adentro de 1% del mejor
                # Y tiene mejor area, entonces usamos esto.
                if ((tp <= (best_tp * ((100 + TP_FLEX_PERCENT) / 100))) and
                    (totalWidth < width)):
                    print("  New best result")
                    result = Result(tp, widths, totalWidth)

            #print("New best Tp: " + str(result.tp) + " Widths " + str(result.widths) + " total widths: " + str(sum(result.widths)) + " reducing simulation time to " + str(sim_time))

        # =====================
        # Actualizar los anchos
        # =====================

        # Usamos los mejores anchos que encontramos y cambiar uno (no el primero)
        widths = result.widths

        # Generar un ancho aleatoriamente entre tech.W_MIN y put.get_max_width()
        width = random.uniform(tech.W_MIN, put.get_max_width())

        # Elegir cual ancho cambiar (no elegimos el primero)
        idx = random.randint(1, len(widths)-1)
        widths[idx] = width

        # Hazlo
        put.set_widths(widths)

    te = time.time();

    # ======================
    # Mostrar los resultados
    # ======================
    print("Took " + str(te - ts) + "s to run " + str(num_sims) + " simulations");
    print("Best Tp " + str(result.tp) + " Widths " + str(result.widths))

    if not os.path.exists("results/"):
        os.mkdir("results/")
    f = open("results/"+type(put).__name__+"_"+tech.NAME+".txt","a+")
    f.write(datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ": Step time " + str(step_time) + " Num sims " + str(num_sims) + " Best Tp " + str(result.tp) + " Widths " + str(result.widths) + "\n")
    f.close()

    # ============================================
    # Encontrar el Tp optimo usando logical effort
    # ============================================
    optWidths = put.get_logical_effort_optimal_widths()
    if (optWidths == None):
        print("Optimal case not supported by this path")
    else:
        print("Running test with optimal widths calculated via logical effort: " + str(optWidths))
        put.set_widths(optWidths)
        tp = _get_tp(circuit, tech, put, sim_time, step_time)

        if (tp <= 0):
            print("Optimal Case: Out never transititons")
        else:
            print("Optimal Case: " + str(tp) + ", widths: " + str(optWidths))

    # ================================================
    # Finalmente simula una vez más con anchos mejores
    # que encontramos y plotear el resultado
    # ================================================
    if (plot_result and (result.tp > 0.0) and (result.tp < 1.0)):
        put.set_widths(result.widths)
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.transient(end_time=sim_time*1.5, step_time=step_time)
        put.plot(analysis, 'In', 'Out')
