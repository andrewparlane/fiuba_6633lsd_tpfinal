import os
from datetime import datetime
import time
import random

import matplotlib.pyplot as plt

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

def _get_widths_str(widths):
    res = ""
    for i, w in enumerate(widths):
        if (i != 0):
            res += ", "
        res += "%.2fe-6" % (w*1e6)

    return res

def _get_tp(circuit, tech, put, sim_time, step_time, logger):
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
            logger.debug("In rises past 50%% at %s", str(in_rises.convert_to_power(-12)))
            break

    # Después encontrar la trasición de la salida
    for (v, t) in zip(analysis['out'], analysis['out'].abscissa):
        # la salida será un flanco ascendente o descendente?
        if (put.inverts()):
            if (float(v) <= (tech.VDD / 2)):
                out_transitions = t
                logger.debug("Out falls past 50%% at %s", str(out_transitions.convert_to_power(-12)))
                break
        else:
            if (float(v) >= (tech.VDD / 2)):
                out_transitions = t
                logger.debug("Out rises past 50%% at %s", str(out_transitions.convert_to_power(-12)))
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
# cvs           - Escribir los resultados a este archivo en formato .cvs (None si no quieres)
# logger        - El logger (debería estar VerboseLogger)
#                 Los niveles usados son: WARNING, INFO, VERBOSE, DEBUG

# Ejemplo:
#   from tech   import TSMC180              as tech     # Tecnologia que queremos usar
#   from paths  import inversor_chain_path  as path     # Path que estamos probando
#   from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo
#
#   logger = verboselogs.VerboseLogger('MCS logger')
#   logger.addHandler(logging.StreamHandler())
#   logger.setLevel(logging.INFO);
#
#   put = path.InversorChainPath(tech, 5)
#   mcs.do_monte_carlo_sim(tech, put, 1e-9, 10000, None, True)

def do_monte_carlo_sim(tech, put, step_time, num_sims, plot_result, cvs, logger):
    # initialisar el generador alatoria usando el tiempo del sistema
    random.seed()

    # Abrir el archivo de .cvs
    if (cvs != None):
        try:
            cvs_handle = open(cvs,"w+")
        except:
            logger.error("Failed to open %s for writing, aborting", cvs)
            return


    logger.info("Running Monte Carlo simulation with path %s, tech %s, with step_time %e, num_sims %d", put.name(), tech.NAME, step_time, num_sims)

    # ==================
    # Generar el netlist
    # ==================
    libraries_path = find_libraries()
    circuit = Circuit("Monte_Carlo_Sim_"+put.name()+"_"+tech.NAME)
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
    # we reduce simulation time to bestResult.tp + 50ps
    succesfull_run = False

    # Hay varios resultados con el mismo (o muy parecido) Tp
    # Si una simulación da un Tp un poco peor (1%?) peor usa menos area, deberíamos
    # usar esto resultado cómo el mejor.
    TP_FLEX_PERCENT = 1.0

    # guardamos el mejor resultado
    bestResult = Result(100.0, put.get_widths())

    # Y guardamos un array de todos los resultados
    allResults = []

    for l in range(1,num_sims+1):

        widths = put.get_widths()
        totalWidth = sum(widths)

        logger.debug("Running simulation with widths: [%s], sim_time %e, step_time %e", _get_widths_str(widths), sim_time, step_time)

        tp = _get_tp(circuit, tech, put, sim_time, step_time, logger)
        if (tp < 0):
            # La duración de simulación no estuvo suficiente largo
            # Si vimos una transición antes, entonces es claro que esto no puede ser mejor.
            # Pero si nunca vimos una transición antes, incrementamos la duración
            if (not succesfull_run):
                sim_time += sim_time_step
                logger.verbose("Out never transititons, increasing simulation time to %e", sim_time)
            else:
                logger.debug("Out never transititons")
        else:
            succesfull_run = True

            logger.verbose("tp: %e, widths: [%s], totalWidth: %e", tp, _get_widths_str(widths), totalWidth)

            allResults.append(Result(tp, widths))

            # este resultado tiene menor tp que el corriente mejor?
            if (tp < bestResult.tp):
                logger.verbose("  New Best Tp")
                bestResult = Result(tp, widths)

                # reducir la duración de la simulación a tp + 50ps
                sim_time = tp + 50e-12

        # =====================
        # Actualizar los anchos
        # =====================

        # Usamos los mejores anchos que encontramos como base
        widths = list(bestResult.widths)    # tomar una copia

        #-------------------------------------------------------------------
        # Método 1: Cambiar todos los ancho aleatoriamente
        #-------------------------------------------------------------------
        #for idx in range(1, len(widths)):
        #    width = random.uniform(tech.W_MIN, put.get_max_width())
        #    widths[idx] = width

        #----------------------------------------------------------------
        # Método 2: Cambiar un ancho aleatoriamente adentro todo el rango
        #----------------------------------------------------------------

        # Generar un ancho aleatoriamente entre tech.W_MIN y put.get_max_width()
        #width = random.uniform(tech.W_MIN, put.get_max_width())

        # Elegir cual ancho cambiar (no elegimos el primero)
        #idx = random.randint(1, len(widths)-1)
        #widths[idx] = width

        #----------------------------------------------------------------------
        # Método 3: Cambiar todos los ancho aleatoriamente en el rango de 0.5w
        #           a 2w. Dónde w es el ancho actual.
        #----------------------------------------------------------------------
        for idx in range(1, len(widths)):
            minWidth = max(tech.W_MIN, widths[idx]/2)
            maxWidth = min(put.get_max_width(), widths[idx]*2)
            width = random.uniform(minWidth, maxWidth)

            logger.debug("curr_width %e, minWidth %e, maxWidth %e, new width %e",
                          widths[idx], minWidth, maxWidth, width)

            widths[idx] = width

        # Hazlo
        put.set_widths(widths)

        if (l % 100 == 0):
            logger.info("Ran %d / %d (%.1f%%)", l, num_sims, (100.0 * l)/num_sims)

    te = time.time();

    # ======================
    # Mostrar los resultados
    # ======================
    logger.info("Took %ds to run %d simulations", int(te - ts), num_sims);
    logger.info("Best Tp %e, Widths [%s]", bestResult.tp, _get_widths_str(bestResult.widths))

    # ============================================
    # Encontrar el Tp optimo usando logical effort
    # ============================================
    LEwidths= put.get_logical_effort_optimal_widths()
    if (LEwidths == None):
        logger.warning("Optimal case not supported by this path")
    else:
        logger.info("Running test with optimal widths calculated via logical effort: [%s]", _get_widths_str(LEwidths))
        put.set_widths(LEwidths)
        LEtp = _get_tp(circuit, tech, put, sim_time, step_time, logger)

        if (LEtp <= 0):
            logger.info("Optimal Case: Out never transititons")
        else:
            logger.info("Optimal Case: %e, widths: [%s]", LEtp, _get_widths_str(LEwidths))

    # ================================================
    # Escribir los resultados al .cvs
    # ================================================
    if (cvs != None):
        # Comenzamos con un comentario
        cvs_handle.write("#%s: Step time %.1e, Num sims %d, path: %s, tech: %s, load: %.2f\n" %
                         (datetime.now().strftime("%Y/%m/%d %H:%M:%S"), step_time,
                          num_sims, put.name(), tech.NAME, put.get_load()))

        # La simulación de LE (comentario)
        if (LEwidths == None):
            cvs_handle.write("#Logical Effort not supported by this path\n")
        elif (LEtp <= 0):
            cvs_handle.write("#Logical Effort: out never transititons\n")
        else:
            cvs_handle.write("#Logical Effort: %e, widths: [%s]\n" %
                             (LEtp, _get_widths_str(LEwidths)))

        # El titulo de los columnos:
        widthHeadings = ""
        for i in range(len(widths)):
            widthHeadings += "width[%d], " % i

        ratioHeadings = ""
        for i in range(len(widths) - 1):
            ratioHeadings += "ratio %d to %d, " % (i, i+1)
        ratioHeadings += "ratio %d to load, " % (i+1)

        cvs_handle.write("Tp, " + widthHeadings + "load width, Total width, " + ratioHeadings + "Average ratio (not including load), Average ratio (including load)\n")

        # Y los resultados
        for r in allResults:

            ratios = []
            for i in range(len(r.widths) - 1):
                ratios.append(r.widths[i+1] / r.widths[i])

            avgWithoutLoad = sum(ratios)/len(ratios)

            ratios.append(put.get_load() * tech.W_MIN / r.widths[i+1])
            avgWithLoad = sum(ratios)/len(ratios)

            ratiosStr = ""
            for i, ratio in enumerate(ratios):
                if (i != 0):
                    ratiosStr += ", "
                ratiosStr += "%.2f" % ratio

            cvs_handle.write("%e, %s, %e, %e, %s, %.2f, %.2f\n" %
                             (r.tp,
                              _get_widths_str(r.widths),
                              put.get_load() * tech.W_MIN,
                              sum(r.widths),
                              ratiosStr,
                              avgWithoutLoad,
                              avgWithLoad))

        cvs_handle.close()

    # ================================================
    # Finalmente simula una vez más con anchos mejores
    # que encontramos y plotear el resultado
    # ================================================
    if (plot_result and (bestResult.tp > 0.0) and (bestResult.tp < 1.0)):
        put.set_widths(bestResult.widths)
        simulator = circuit.simulator(temperature=27, nominal_temperature=27)
        analysis = simulator.transient(end_time=sim_time*1.5, step_time=step_time)
        put.plot(analysis, 'In', 'Out')
