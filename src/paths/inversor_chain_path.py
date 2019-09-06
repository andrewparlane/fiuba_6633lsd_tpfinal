from PySpice.Spice.Netlist import Circuit
import matplotlib.pyplot as plt
from PySpice.Probe.Plot import plot

import random

class InversorChainPath:

    __inv               = None
    __tech              = None
    __num_inversores    = 0
    __inversores        = []

    def __init__(self, tech, num_inversores):
        super().__init__()

        # Initializar los variables del clase
        self.__tech             = tech
        self.__inv              = tech.Inversor()
        self.__num_inversores   = num_inversores
        self.__inversores       = [];

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

        # Generar la cadena de inversores
        # guardando cada inversor en __inversores
        # todos comienzan con el ancho mínimo
        for i in range(self.__num_inversores):
            inNode = pathInNode if i == 0 else ('tmp' + str(i))
            outNode = pathOutNode if i == (self.__num_inversores - 1) else ('tmp' + str(i+1))
            self.__inversores.append(self.__inv.add_instance(circuit, i, VddNode, [inNode], outNode, self.__tech.W_MIN))

        # La carga - usamos un inversor de tamaño 8 veces el ancho mínimo
        # no lo añadimos a la lista, porque no queremos cambiar los ancho más tarde
        for i in range(8):
            self.__inv.add_instance(circuit, self.__num_inversores + i, VddNode, ['out'], 'loadOut' + str(i), self.__tech.W_MIN)

    # Un flanco ascendente en la entrada da un flanco descendente en la salida?
    def inverts(self):
        return (self.__num_inversores % 2) == 1

    def get_widths(self):
        widths = []
        for inv in self.__inversores:
            widths.append(inv.parameters["w"])
        return widths

    # Solo deberías pasar un valor que viene de get_width(),
    # y no cambiar los valores manualmente
    def set_widths(self, widths):
        for idx, w in enumerate(widths):
            self.__inversores[idx].parameters["w"] = w

    def change_one_width(self):
        # Generar un ancho aleatoriamente
        # todo: deberíamos defenir el ancho máximo y el escalon en algún sitio
        width = self.__tech.W_MIN + (random.randint(0, 2000) * 0.01e-6);

        # Elegir cual ancho cambiar (no elegimos el primero)
        idx = random.randint(1, self.__num_inversores - 1)

        # Hazlo
        self.__inversores[idx].parameters["w"] = width

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
