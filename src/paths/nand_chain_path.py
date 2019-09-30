from PySpice.Spice.Netlist import Circuit
import matplotlib.pyplot as plt
from PySpice.Probe.Plot import plot

import random

class NandChainPath:

    __nand              = None
    __inverter          = None
    __tech              = None
    __num_gates         = 0
    __gates             = []
    __load              = 32.0  # La carga es un inversor de tamaño __load * tech.W_MIN

    def __init__(self, tech, num_gates, load):
        super().__init__()

        # Initializar los variables del clase
        self.__tech             = tech
        self.__nand             = tech.Nand()
        self.__inverter         = tech.Inversor()
        self.__num_gates        = num_gates
        self.__load             = load
        self.__gates            = []
        self.__inputSources     = []

    def name(self):
        return str("nand_chain_" + str(self.__num_gates))

    # Esto solo es para usar con pruebas de rutas
    # Si cambias esos valores un flanco en la entrada
    # tal vez no va a propogar a la salida
    def get_input_sources(self):
        return self.__inputSources

    def get_output_value(self, inputs):
        # La lista de entradas (inputs) es en forma:
        # pathInNode, PathInB0, PathInB1, ...
        # Vamos por cada etapa
        result = inputs[0]
        for i in range(self.__num_gates):
            # Puedo usar get_output_value de la compuerta aquí
            # pero creo que es mejor calcular le manualmente
            result = not (result and inputs[i+1])
        return result

    def add_to_circuit(self, circuit, VddNode, pathInNode, pathOutNode):
        __gates         = []
        __inputSources  = []

        # Añadir el NAND y Inversor subcircuito al netlist
        circuit.subcircuit(self.__nand)
        circuit.subcircuit(self.__inverter)

        # Generar la cadena de NANDs
        # guardando cada compuerta en __gates
        # todos comienzan con el ancho mínimo
        # Conectar todas las entradas Bs a su propio fuente (Vdd)
        # y guardar una lista de los fuentes: __inputSources
        for i in range(self.__num_gates):
            inNodeA = pathInNode if i == 0 else ('tmp' + str(i))
            inNodeB = "PathInB" + str(i)
            outNode = pathOutNode if i == (self.__num_gates - 1) else ('tmp' + str(i+1))
            self.__inputSources.append(circuit.V(inNodeB, inNodeB, circuit.gnd, self.__tech.VDD))
            self.__gates.append(self.__nand.add_instance(circuit, i, VddNode, [inNodeA, inNodeB], outNode, self.__tech.W_MIN))

        # La carga - usamos un inversor de tamaño __load veces el ancho mínimo
        # no lo añadimos a la lista, porque no queremos cambiar los ancho más tarde
        self.__inverter.add_instance(circuit, "load", VddNode, ['out'], 'loadOut', self.__tech.W_MIN * self.__load)


    # Un flanco ascendente en la entrada da un flanco descendente en la salida?
    def inverts(self):
        return (self.__num_gates % 2) == 1

    def get_widths(self):
        widths = []
        for g in self.__gates:
            widths.append(g.parameters["w"])
        return widths

    def get_max_width(self):
        # La carga es un inversor de ancho __load * tech.W_MIN, así elegimos un ancho máximo
        # de un poco más grande. Puede ser más pequeño de la carga, pero quiero darle un
        # poco más flexibilidad
        return 1.25 * self.__load * self.__tech.W_MIN

    # todos los anchos deberían estar entre tech.W_MIN y get_max_width()
    def set_widths(self, widths):
        for idx, w in enumerate(widths):
            self.__gates[idx].parameters["w"] = w

    def get_logical_effort_optimal_widths(self):
        return None

    def plot(self, analysis, pathInNode, pathOutNode):
        figure = plt.figure(1, (10, 5))
        axe = plt.subplot(111)
        plt.title('')
        plt.xlabel('Time [s]')
        plt.ylabel('Voltage [V]')
        plt.grid()
        plot(analysis[pathInNode], axis=axe)

        ledgend = ['In']

        for i in range(self.__num_gates - 1):
            node = "tmp" + str(i+1)
            plot(analysis[node], axis=axe)
            ledgend.append(node)

        ledgend.append(pathOutNode)

        plot(analysis[pathOutNode], axis=axe)
        plt.legend(ledgend, loc=(.05,.1))

        plt.tight_layout()
        plt.show()
