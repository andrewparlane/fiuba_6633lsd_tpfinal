import argparse

from tech   import TSMC180              as tech     # Tecnologia que queremos usar

# Rutas
from paths  import inversor_chain_path  as icp
from paths  import nand_chain_path      as ncp

# Simulaciones
from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo
from sims   import gate_test            as gt       # El código que hace pruebas de compuertas
from sims   import path_test            as pt       # El código que hace pruebas de rutas

def inverter_chain_3():
    return icp.InversorChainPath(tech, 3)

def inverter_chain_5():
    return icp.InversorChainPath(tech, 5)

def nand_chain_5():
    return ncp.NandChainPath(tech, 5)

def inverter():
    return tech.Inversor()

def nand():
    return tech.Nand()

def nor():
    return tech.Nor()

PATHS = {
            'inverter_chain_3'  : inverter_chain_3,
            'inverter_chain_5'  : inverter_chain_5,
            'nand_chain_5'      : nand_chain_5,
            #'FO4'               : test2
        }

GATES = {
            'inverter'          : inverter,
            'NAND'              : nand,
            'NOR'               : nor
        }

def do_mcs(args):
    step_time   = args.step_time
    num_sims    = args.num_sims
    path        = args.path
    plot_result = args.plot_result

    put = PATHS[path]()
    mcs.do_monte_carlo_sim(tech, put, step_time, num_sims, plot_result)

def do_gt(args):
    gate = args.gate

    gut = GATES[gate]()
    gt.do_gate_test(tech, gut)

def do_pt(args):
    path = args.path

    put = PATHS[path]()
    pt.do_path_test(tech, put)

# ====================
# Parseo de argumentos
# ====================

parser = argparse.ArgumentParser(description='Run tests / simulation using TSMC180 tech')
subparsers = parser.add_subparsers(title='Commands', metavar='CMD', required=True)

parserMCS = subparsers.add_parser('MCS', help='Monte Carlo Simulation')
parserMCS.add_argument('--step_time', metavar='TIME', type=float, default=1e-9,
                       help='Max time step for transient simulation (default: 1e-9)')
parserMCS.add_argument('--num_sims', type=int, default=10000,
                       help='Number of simulation to run (default: 10000)')
parserMCS.add_argument('-p', '--plot', dest='plot_result', action='store_true', default=False,
                       help='Plot the results of the transient sim of the best case')
parserMCS.add_argument('path', metavar='PATH', choices=PATHS,
                       help='Path to simulate: (%(choices)s)')
parserMCS.set_defaults(func=do_mcs)

parserGT = subparsers.add_parser('GT', help='Gate Test')
parserGT.add_argument('gate', metavar='GATE', choices=GATES,
                      help='Gate to test: (%(choices)s)')
parserGT.set_defaults(func=do_gt)

parserGT = subparsers.add_parser('PT', help='Path Test')
parserGT.add_argument('path', metavar='PATH', choices=PATHS,
                      help='Gate to test: (%(choices)s)')
parserGT.set_defaults(func=do_pt)

args = parser.parse_args()
args.func(args)
