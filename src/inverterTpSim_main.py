import logging
import verboselogs
import sys
import numpy as np
from tech import TSMC180 as tech     # Tecnologia que queremos usar
from paths import inversor_chain_path as icp
import matplotlib.pyplot as plt

from PySpice.Doc.ExampleTools import find_libraries
from PySpice.Probe.Plot import plot
from PySpice.Spice.Library import SpiceLibrary
from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Unit import *


def main():
    logger = verboselogs.VerboseLogger('InverterTpSim logger')
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)
    step_time = 1e-13
    sim_time = 2000e-12
    
    put = icp.InversorChainPath(tech, 1, 32.0)
    # ==================
    # Generar el netlist
    # ==================
    libraries_path = find_libraries()
    circuit = Circuit("Monte_Carlo_Sim_"+put.name()+"_"+tech.NAME)
    # .inclcude "foo.lib"
    circuit.include(libraries_path + "/" + tech.LIB_NAME)

    # Fuente de tensión Vdd
    vdd = circuit.V('dd', 'Vdd', circuit.gnd, tech.VDD)

    # Fuente de tensión de pulses que usamos como la entrada de la ruta
    vin = circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=tech.VDD,
                                     pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)

    # La ruta que queremos probar
    put.add_to_circuit(circuit, 'Vdd', 'In', 'Out')
    widths = np.arange(tech.W_MIN, tech.W_MIN*16, tech.W_MIN/10.0).tolist()
    tps = []
    for width in widths:
        v = []
        v.append(width)
        put.set_widths(v)
        tps.append(_get_tp_inv(circuit,
                               tech, put,
                               sim_time, step_time, 80.0, 20.0, logger))
    fig, axs = plt.subplots(1)
    axs.set_title('Porpagation time by gate width (32*WIDTH_MIN load)')
    axs.plot([(w / tech.W_MIN)**(-1) for w in widths] , [tp / 1e-12 for tp in tps], 'ro')
    axs.set_xlabel('1/GATE_WIDTH [MIN_WIDTH normalized]')
    axs.set_ylabel('propagation time [10^(-12) seg]')
    
    plt.show()


def _get_tp_inv(circuit, tech, put, sim_time, step_time, v_in_rise, v_out_fall, logger):

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

    # Primero encontrar la transición de la entrada
    for (v, t) in zip(analysis['in'], analysis['in'].abscissa):
        if (float(v) >= (tech.VDD * (v_in_rise/100.0))):
            in_rises = t
            logger.debug("In rises past " + str(v_in_rise) +
                         "%% at %s", str(in_rises.convert_to_power(-12)))
            break

    # Después encontrar la trasición de la salida
    for (v, t) in zip(analysis['out'], analysis['out'].abscissa):
        # la salida será un flanco ascendente o descendente?
        if (put.inverts()):
            if (float(v) <= (tech.VDD * (v_out_fall/100.0))):
                out_transitions = t
                logger.debug("Out falls " + str(v_out_fall)+"%% at %s",
                             str(out_transitions.convert_to_power(-12)))
                break
        else:
            if (float(v) >= (tech.VDD * (v_out_fall/100))):
                out_transitions = t
                logger.debug("Out rises past "+ str(v_out_fall) + "%% at %s", str(
                    out_transitions.convert_to_power(-12)))
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


if __name__ == '__main__':
    main()
