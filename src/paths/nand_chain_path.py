from PySpice.Spice.Netlist import Circuit
import matplotlib.pyplot as plt
from PySpice.Probe.Plot import plot

import random

class NandChainPath:

    __nand              = None
    __tech              = None
    __num_gates         = 0
    __gates             = []

    def __init__(self, tech, num_gates):
        super().__init__()

        # Initializar los variables del clase
        self.__tech             = tech
        self.__nand             = tech.Nand()
        self.__num_gates        = num_gates
        self.__gates            = []
        self.__inputSources     = []

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
        # Añadir el NAND subcircuito al netlist
        circuit.subcircuit(self.__nand)

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

        # La carga
        carga = circuit.C(1, 'Out', circuit.gnd, 500e-15)

    # Un flanco ascendente en la entrada da un flanco descendente en la salida?
    def inverts(self):
        return (self.__num_gates % 2) == 1

    def get_widths(self):
        widths = []
        for g in self.__gates:
            widths.append(g.parameters["w"])
        return widths

    # Solo deberías pasar un valor que viene de get_width(),
    # y no cambiar los valores manualmente
    def set_widths(self, widths):
        for idx, w in enumerate(widths):
            self.__gates[idx].parameters["w"] = w

    def change_one_width(self):
        # Generar un ancho aleatoriamente
        # todo: deberíamos defenir el ancho máximo y el escalon en algún sitio
        width = self.__tech.W_MIN + (random.randint(0, 2000) * 0.01e-6);

        # Elegir cual ancho cambiar (no elegimos el primero)
        idx = random.randint(1, self.__num_gates - 1)

        # Hazlo
        self.__gates[idx].parameters["w"] = width

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
