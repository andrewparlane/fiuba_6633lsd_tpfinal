import argparse
import logging, verboselogs
import sys

from tech   import TSMC180              as tech     # Tecnologia que queremos usar

# Rutas
from paths  import inversor_chain_path  as icp
from paths  import nand_chain_path      as ncp

# Simulaciones
from sims   import monte_carlo_sim      as mcs      # El código que hace la simulación Monte Carlo
from sims   import gate_test            as gt       # El código que hace pruebas de compuertas
from sims   import path_test            as pt       # El código que hace pruebas de rutas

def inverter_chain(len, load):
    return icp.InversorChainPath(tech, len, load)

def nand_chain(len, load):
    return ncp.NandChainPath(tech, len, load)

def inverter():
    return tech.Inversor()

def nand():
    return tech.Nand()

def nor():
    return tech.Nor()

PATHS = {
            'inverter_chain_3'  : (inverter_chain, 3),
            'inverter_chain_4'  : (inverter_chain, 4),
            'inverter_chain_5'  : (inverter_chain, 5),
            'inverter_chain_6'  : (inverter_chain, 6),
            'nand_chain_5'      : (nand_chain,     5)
        }

GATES = {
            'inverter'          : inverter,
            'NAND'              : nand,
            'NOR'               : nor
        }

def do_mcs(args, logger):
    step_time   = args.step_time
    num_sims    = args.num_sims
    path        = args.path
    load        = args.load
    plot_result = args.plot_result

    func, len = PATHS[path]
    put = func(len, load)
    mcs.do_monte_carlo_sim(tech, put, step_time, num_sims, plot_result, logger)

def do_gt(args, logger):
    gate = args.gate

    gut = GATES[gate]()
    gt.do_gate_test(tech, gut)

def do_pt(args, logger):
    path = args.path
    load = args.load

    func, len = PATHS[path]
    put = func(len, load)
    pt.do_path_test(tech, put)

# ====================
# Parseo de argumentos
# ====================

def load_type(load):
    load = float(load)
    if load < 1.0:
        raise argparse.ArgumentTypeError("Minimum load is 1.0")
    return load


def main():
    parser = argparse.ArgumentParser(description='Run tests / simulation using TSMC180 tech')
    subparsers = parser.add_subparsers(title='Commands', metavar='CMD', required=True)

    verbosityGroup = parser.add_mutually_exclusive_group()
    verbosityGroup.add_argument('-v', dest='verbose', action='store_true', default=False,
                                help='Output debug information')
    verbosityGroup.add_argument('-vv', dest='verbose2', action='store_true', default=False,
                                help='Output lots of debug information')
    verbosityGroup.add_argument('-q', dest='quiet', action='store_true', default=False,
                                help='Output nothing')

    parserMCS = subparsers.add_parser('MCS', help='Monte Carlo Simulation')
    parserMCS.add_argument('--step_time', metavar='TIME', type=float, default=1e-13,
                           help='Max time step for transient simulation (default: 1e-13)')
    parserMCS.add_argument('--num_sims', type=int, default=10000,
                           help='Number of simulation to run (default: 10000)')
    parserMCS.add_argument('--load', metavar='LOAD', type=load_type, required=True,
                           help='The load is an inversor of width LOAD * W_MIN')
    parserMCS.add_argument('-p', '--plot', dest='plot_result', action='store_true', default=False,
                           help='Plot the results of the transient sim of the best case')
    parserMCS.add_argument('path', metavar='PATH', choices=PATHS,
                           help='Path to simulate: (%(choices)s)')
    parserMCS.set_defaults(func=do_mcs)

    parserGT = subparsers.add_parser('GT', help='Gate Test')
    parserGT.add_argument('gate', metavar='GATE', choices=GATES,
                          help='Gate to test: (%(choices)s)')
    parserGT.set_defaults(func=do_gt)

    parserPT = subparsers.add_parser('PT', help='Path Test')
    parserPT.add_argument('path', metavar='PATH', choices=PATHS,
                          help='Gate to test: (%(choices)s)')
    # load doesn't matter, but do need a value to instantiate the path
    parserPT.add_argument('--load', metavar='LOAD', type=load_type, required=False,
                           default=1.0, help=argparse.SUPPRESS)
    parserPT.set_defaults(func=do_pt)

    args = parser.parse_args()

    logger = verboselogs.VerboseLogger('MCS logger')
    logger.addHandler(logging.StreamHandler(sys.stdout))

    # Estos están en un grupo de exclusividad mutual
    if (args.verbose2):
        logger.setLevel(logging.DEBUG)
    elif (args.verbose):
        logger.setLevel(logging.VERBOSE);
    elif (args.quiet):
        logger.setLevel(logging.WARNING);
    else:
        logger.setLevel(logging.INFO);

    args.func(args, logger)

if __name__ == '__main__':
    main()
