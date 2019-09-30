from PySpice.Spice.Netlist import Circuit
import matplotlib.pyplot as plt
from PySpice.Probe.Plot import plot

import random

class InversorChainPath:

    __inv               = None
    __tech              = None
    __num_inversores    = 0
    __inversores        = []
    __load              = 32.0  # La carga es un inversor de tamaño __load * tech.W_MIN

    def __init__(self, tech, num_inversores, load):
        super().__init__()

        # Initializar los variables del clase
        self.__tech             = tech
        self.__inv              = tech.Inversor()
        self.__num_inversores   = num_inversores
        self.__inversores       = [];
        self.__load             = load

    def name(self):
        return str("inversor_chain_" + str(self.__num_inversores))

    # Esto solo es para usar con pruebas de rutas
    # Si cambias esos valores un flanco en la entrada
    # tal vez no va a propogar a la salida
    def get_input_sources(self):
        return []

    def get_output_value(self, inputs):
        if (self.inverts()):
            return (not inputs[0])
        else:
            return inputs[0]

    def add_to_circuit(self, circuit, VddNode, pathInNode, pathOutNode):
        # Añadir el inversor subcircuito al netlist
        circuit.subcircuit(self.__inv)
        self.__inversores = []

        # Generar la cadena de inversores
        # guardando cada inversor en __inversores
        # todos comienzan con el ancho mínimo
        for i in range(self.__num_inversores):
            inNode = pathInNode if i == 0 else ('tmp' + str(i))
            outNode = pathOutNode if i == (self.__num_inversores - 1) else ('tmp' + str(i+1))
            self.__inversores.append(self.__inv.add_instance(circuit, i, VddNode, [inNode], outNode, self.__tech.W_MIN))

        # La carga - usamos un inversor de tamaño __load veces el ancho mínimo
        # no lo añadimos a la lista, porque no queremos cambiar los ancho más tarde
        self.__inv.add_instance(circuit, "load", VddNode, ['out'], 'loadOut', self.__tech.W_MIN * self.__load)

    # Un flanco ascendente en la entrada da un flanco descendente en la salida?
    def inverts(self):
        return (self.__num_inversores % 2) == 1

    def get_widths(self):
        widths = []
        for inv in self.__inversores:
            widths.append(inv.parameters["w"])
        return widths

    def get_max_width(self):
        # La carga es __load*tech.W_MIN, así elegimos un ancho máximo de un poco más grande.
        # Puede ser más pequeño de la carga, pero quiero darle un poco más flexibilidad
        #
        return 1.25 * self.__load * self.__tech.W_MIN

    # todos los anchos deberían estar entre tech.W_MIN y get_max_width()
    def set_widths(self, widths):
        for idx, w in enumerate(widths):
            self.__inversores[idx].parameters["w"] = w

    def get_logical_effort_optimal_widths(self):
        # logical effort dice que la esfuerza de cada etapa debería estar igual:
        # f = gh. g = 1 por un inversor, así f = h = Cout / Cin
        # O el ratio de los anchos debería estar igual.
        # La carga tiene ancho __load*W_MIN, y el primer inversor tiene ancho W_MIN
        # así f_opt = F^(1/N) = __load^(1/N)
        f_opt = self.__load ** (1.0/self.__num_inversores)
        widths = [self.__tech.W_MIN]
        for i in range(1, self.__num_inversores):
            widths.append(widths[i-1] * f_opt)
        return widths

    def plot(self, analysis, pathInNode, pathOutNode):
        figure = plt.figure(1, (10, 5))
        axe = plt.subplot(111)
        plt.title('')
        plt.xlabel('Time [s]')
        plt.ylabel('Voltage [V]')
        plt.grid()
        plot(analysis[pathInNode], axis=axe)

        ledgend = ['In']

        for i in range(self.__num_inversores - 1):
            node = "tmp" + str(i+1)
            plot(analysis[node], axis=axe)
            ledgend.append(node)

        ledgend.append(pathOutNode)

        plot(analysis[pathOutNode], axis=axe)
        plt.legend(ledgend, loc=(.05,.1))

        plt.tight_layout()
        plt.show()
