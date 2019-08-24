#import os

from PySpice.Spice.Netlist import Circuit, SubCircuit, SubCircuitFactory
from PySpice.Unit import *

#import numpy as np

# ======================
# Constantes del proceso
# TSMC 180 - CL018G
# ======================
NAME        = "TSMC180"
LIB_NAME    = "TSMC180.lib"
VDD         = 1.8           # Tensión de Vdd = 1.8V
L_MIN       = 0.18e-6       # Largo de canal mínimo = 0.18 um
W_MIN       = 0.42e-6       # Ancho del transistor mínimo = 0.42 um
LD_MIN      = 0.48e-6       # Largo de difusión mínimo = 0.48 um

# El tiempo de propagación promedio de un inversor con carga de otro inversor igual
# es óptimo cuando el transistor P es 1.5 veces más grande que el transistor N.
# Ver LTSpice_tests/wpfact.asc y "plot .step'ed .meas data"
WPFACT      = 1.5

""" Compuerta:
        base para definir una subcircuito para una compuerta
        El subcircuito tiene 3 parámetros por defecto:
            W - el ancho básico del transistor
            L - El largo de canal
            LD - El largo de difusión
        Sugiero que solo usas W
        Puedes pasar otros parámetros al __init__ desde el clase padre
"""

class Compuerta(SubCircuitFactory):
    __name__ = None
    __nodes__ = None

    __num_inputs = 0

    def __init__(self, num_inputs, **kwargs):
        super().__init__(W=W_MIN, L=L_MIN, LD=LD_MIN, **kwargs)
        self.__num_inputs = num_inputs

    def get_num_inputs(self):
        return self.__num_inputs

    """ create_transistor:
            Todos los llamadas de create_transistor deben ser antes
            de que el subcircuito es añadido al circuito con una llamada a
            circuit.subcircuit(...)

            argumentos:
                model       - debe ser "CMOSN" o "CMOSP"
                name        - nombre del subcircuito e.g. "Inversor"
                drainNode   - nombre del nodo en el subcircuito que es conectado
                              al drain del transistor
                gateNode    - nombre del nodo en el subcircuito que es conectado
                              al gate del transistor
                sourceNode  - nombre del nodo en el subcircuito que es conectado
                              al source del transistor
                bulkNode    - nombre del nodo en el subcircuito que es conectado
                              al bulkNode del transistor
                wMult       - El subcircuito tiene un parámetro de W (ancho básico
                              del transistor) pero los transistores P están dos
                              veces más grande de los Ns, así puedes pasar 2 aquí.
                              También en una compuerta NAND los dos transistores N
                              están en seri, así los dos quieren estar dos veces
                              más grande.

    """
    def create_transistor(self, model, name, drainNode, gateNode, sourceNode, bulkNode, wMult):

        # wMult es un argumento a esta función que pasas cuándo diseñas
        # el subcircuito.

        # W es un parámetro del subcircuito que pasas cuando instancias
        # el subcircuito.

        # El ancho de este transistor es W * wMult
        w = "{W * " + str(wMult) + "}"

        # la aread de difusión es el ancho del transistor por
        # el largo de difusión: (W * wMult) * LD
        area = "{W * " + str(wMult) + " * LD}"

        # El perimetro de difusión solo debería estar los tres lados que no
        # están abajos de la compuerta. Así es es el ancho del transistor y
        # dos veces el largo de difusión: (W * wMult) + (2 * LD)
        perim = "{(W * " + str(wMult) + ") + (2 * LD)}"

        self.M(name,
               drainNode,
               gateNode,
               sourceNode,
               bulkNode,
               model=model,
               width=w,
               length="{L}",
               drain_area=area,
               source_area=area,
               drain_perimeter=perim,
               source_perimeter=perim)

    """ create_transistorN:
            ver el comentario de create_transistor por los argumentos
    """
    def create_transistorN(self, name, drainNode, gateNode, sourceNode, bulkNode, wMult):
        self.create_transistor("CMOSN", name, drainNode, gateNode, sourceNode, bulkNode, wMult)

    """ create_transistorP:
            ver el comentario de create_transistor por los argumentos
    """
    def create_transistorP(self, name, drainNode, gateNode, sourceNode, bulkNode, wMult):
        self.create_transistor("CMOSP", name, drainNode, gateNode, sourceNode, bulkNode, wMult)

# =============================================================================
# Inversor
# =============================================================================
# Ver inversor.asc
# Nota que el transistor P es dos veces el ancho del transistor N
# =============================================================================

class Inversor(Compuerta):
    __name__ = 'inversor'
    __nodes__ = ('Vdd', 'In', 'Out')

    def __init__(self):
        super().__init__(num_inputs=1)
        self.create_transistorN(1, 'Out', 'In', self.gnd, self.gnd, 1)
        self.create_transistorP(2, 'Out', 'In', 'Vdd', 'Vdd', WPFACT)

    def get_output_value(self, inputs):
        return not inputs[0]

    """ add_instance:
            añadir una inversor al circuito
            Es necesario añadir el subcircuito al netlist también
            con una llamada: circuit.subcircuit(Inversor())

            ejemplo:
                circuit = Circuit('Transistor')
                circuit.include("V35G-spice.lib")
                inv = Inversor()
                circuit.subcircuit(inv)
                circuit.V('dd', 'Vdd', circuit.gnd, 5)
                circuit.PulseVoltageSource("In", "In", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)
                inv.add_instance(circuit, 1, 'Vdd', ['In'], 'Out', 2.4e-6)

            argumentos:
                circuit     - El circuito / subcircuito donde quieres
                              añadir la compuerta
                name        - nombre / número de la compuerta
                vddNode     - el nodo de Vdd
                inNodes     - las entradas de la compuerta (solo debería estar 1)
                outNode     - la salida de la compuerta
                w           - El ancho del transistor N. El ancho del
                              transistor P es dos veces más grande
    """
    def add_instance(self, circuit, name, vddNode, inNodes, outNode, w):
        return circuit.X("Inv" + str(name), "Inversor", vddNode, inNodes[0], outNode, w=w)


# =============================================================================
# NAND
# =============================================================================
# Ver nand.asc
# Nota que todos los transistores son w * 2
# =============================================================================

class Nand(Compuerta):
    __name__ = 'nand'
    __nodes__ = ('Vdd', 'InA', 'InB', 'Out')

    def __init__(self):
        super().__init__(num_inputs=2)
        self.create_transistorN(1, 'Out', 'InA', 'tmpN', self.gnd, 2)
        self.create_transistorN(2, 'tmpN', 'InB', self.gnd, self.gnd, 2)
        self.create_transistorP(3, 'Out', 'InA', 'Vdd', 'Vdd', WPFACT)
        self.create_transistorP(4, 'Out', 'InB', 'Vdd', 'Vdd', WPFACT)

    def get_output_value(self, inputs):
        return not (inputs[0] and inputs[1])

    """ add_instance:
            añadir una NAND al circuito
            Es necesario añadir el subcircuito al netlist también
            con una llamada: circuit.subcircuit(NAND())

            ejemplo:
                circuit = Circuit('Transistor')
                circuit.include("V35G-spice.lib")
                nand = NAND()
                circuit.subcircuit(nand)
                circuit.V('dd', 'Vdd', circuit.gnd, 5)
                circuit.PulseVoltageSource("InA", "InA", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)
                circuit.PulseVoltageSource("InB", "InB", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=2e-9, period=4e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)
                nand.add_instance(circuit, 1, 'Vdd', ['InA', 'InB'], 'Out', 2.4e-6)

            argumentos:
                circuit     - El circuito / subcircuito donde quieres
                              añadir la compuerta
                name        - nombre / número de la compuerta
                vddNode     - el nodo de Vdd
                inNodes     - las entradas de la compuerta (solo debería estar 2)
                outNode     - la salida de la compuerta
                w           - El ancho básico. Todos los transistores
                              tienen un ancho W * 2
    """
    def add_instance(self, circuit, name, vddNode, inNodes, outNode, w):
        return circuit.X("Nand" + str(name), "nand", vddNode, inNodes[0], inNodes[1], outNode, w=w)


# =============================================================================
# NOR
# =============================================================================
# Ver nor.asc
# Nota que los transistores P son W * 4, y los transistores N son W
# =============================================================================

class Nor(Compuerta):
    __name__ = 'nor'
    __nodes__ = ('Vdd', 'InA', 'InB', 'Out')

    def __init__(self):
        super().__init__(num_inputs=2)
        self.create_transistorN(1, 'Out', 'InA', self.gnd, self.gnd, 1)
        self.create_transistorN(2, 'Out', 'InB', self.gnd, self.gnd, 1)
        self.create_transistorP(3, 'Out', 'InA', 'tmpP', 'Vdd', WPFACT * 2)
        self.create_transistorP(4, 'tmpP', 'InB', 'Vdd', 'Vdd', WPFACT * 2)

    def get_output_value(self, inputs):
        return not (inputs[0] or inputs[1])

    """ add_instance:
            añadir un NOR al circuito
            Es necesario añadir el subcircuito al netlist también
            con una llamada: circuit.subcircuit(NOR())

            ejemplo:
                circuit = Circuit('Transistor')
                circuit.include("V35G-spice.lib")
                nor = NOR()
                circuit.subcircuit(nor)
                circuit.V('dd', 'Vdd', circuit.gnd, 5)
                circuit.PulseVoltageSource("InA", "InA", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=1e-9, period=2e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)
                circuit.PulseVoltageSource("InB", "InB", circuit.gnd, initial_value=0, pulsed_value=5, pulse_width=2e-9, period=4e-9, delay_time=10e-12, rise_time=20e-12, fall_time=20e-12)
                nor.add_instance(circuit, 1, 'Vdd', ['InA', 'InB'], 'Out', 2.4e-6)

            argumentos:
                circuit     - El circuito / subcircuito donde quieres
                              añadir la compuerta
                name        - nombre / número de la compuerta
                vddNode     - el nodo de Vdd
                inNodes     - las entradas de la compuerta (solo debería estar 2)
                outNode     - la salida de la compuerta
                w           - El ancho de los transistores N.
                              Los transistores P tienen ancho = w * 4.
    """
    def add_instance(self, circuit, name, vddNode, inNodes, outNode, w):
        return circuit.X("Nor" + str(name), "nor", vddNode, inNodes[0], inNodes[1], outNode, w=w)
