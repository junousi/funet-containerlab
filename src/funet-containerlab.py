#!/usr/bin/env python3

import sys, re, csv
import networkx as nx
from operator import itemgetter
from optparse import OptionParser
from geopy.distance import geodesic

def join_digits(string):
    """
    Join router interface digits to single integer e.g.
    et-1/0/7 -> 107
    """
    return re.sub('[^0-9]', '', string)

def get_if_index(node, interface, graph):
    """
    For a given node and target interface, sort all the interfaces of that node
    and provide the index of the target interface within that sorted list.
    """
    if_indices = {}

    for n, nbrs in graph.adjacency():
        if n != node:
            continue
        for nbr in nbrs:
            if_indices[ graph[node][nbr]['interface']] = \
            join_digits(graph[node][nbr]['interface'])

    sorted_if_indices = dict(sorted(if_indices.items(), key=itemgetter(1)))

    return list(sorted_if_indices.keys()).index(interface)

def parse_netmap_topo(topofile):
    """
    Parse the network load map.
    """
    g = nx.DiGraph()
    with open(topofile, 'r') as f:
        src = dst = ''
        for line in f:
            if line.startswith('<!-- Funet geographical load map'):
                pass
            elif line.startswith('<!--'):
                # Don't include IX/etc for now.
                m1 = re.match(r"<!-- ([a-z0-9]+).ip.funet.fi", line)
                if m1 != None:
                    src = m1.group(1)
                    g.add_node(src)
                m2 = re.match(r".* ([a-z0-9]+).ip.funet.fi -->", line)
                if m2 != None:
                    dst = m2.group(1)
                    g.add_node(dst)
            elif 'addTo' in line:
                src = dst = ''
                continue
            elif 'interface' in line:
                m3 = re.match(r".*interface=([^\"\.]+)", line)
                if src != '' and dst != '' and m3 != None:
                    interface=m3.group(1)
                    g.add_edge(src, dst, interface=interface)
    return g

def output_yaml(hd_graph, fd_graph, image, kind, out):
    """
    Output a containerlab-compatible topology to stdout.
    """
    out.write('''---
name: funet-containerlab
mgmt:
  bridge: virbr0
  ipv4-subnet: 192.168.42.0/24
topology:\n''')
    out.write('''  defaults:
    kind: {kind}
    image: {image}
    startup-config: __clabNodeName__.cfg\n'''.format(kind=kind, image=image))
    out.write('  nodes:\n')
    for index, n in enumerate(hd_graph.nodes):
        out.write('''    {router}:
      mgmt-ipv4: 192.168.42.{index}\n'''.format(router=n, index=index+100))
    out.write('  links:\n')
    # The source HTML does not contain full-duplex interface data, thus we
    # need to work with two graphs; one that holds the half-duplex links wanted
    # by containerlab topology parser, and the other which has awareness of the
    # specific router interface for B in the case of A->B.
    for src, dst, dummyattr in hd_graph.edges.data():
        out.write('    - endpoints: ["{rtr1}:{if1}", "{rtr2}:{if2}"]\n'.format(
            rtr1 = src,
            if1  = 'et-0/0/' + str(get_if_index(src,
                                                fd_graph[src][dst]['interface'],
                                                fd_graph)),
            rtr2 = dst,
            if2  = 'et-0/0/' + str(get_if_index(dst,
                                                fd_graph[dst][src]['interface'],
                                                fd_graph))))

# Initial geographical latency implementation with halfduplex graph;
# something more reasonable could be fullduplex graph with both endpoints'
# delay set to geo_delay/2. TODO
# Also the excludelist should be extended to the topology parser.
def output_netem_commands(hd_graph, fd_graph, out):

    reader = csv.reader(open('./coordinates.csv', 'r'))
    locations = {}
    for row in reader:
        location, n, e = row
        locations[location] = [n, e]

    excludelist = ['Stockholm', 'Kalix', 'Sundsvall']

    for src, dst, attributes in hd_graph.edges.data():

        owd = 0

        # Reformat to match source data
        node1_loc = ''.join([i for i in src if not i.isdigit()]).capitalize()
        node2_loc = ''.join([i for i in dst if not i.isdigit()]).capitalize()

        if node1_loc in excludelist or node2_loc in excludelist:
            continue
        if node1_loc == node2_loc:
            # Arbitrary nonzero µs delay for back-to-back routers case
            owd = 100
        else:
            # Includes:
            # - Approx. speed of light in fiber 200 m/µs
            # - Path adjustment +10%
            # - Equipment latency (~1ms might be slightly naive but gives decent correlation)
            # For further consideration:
            # - Local loop lengths (or just factor more into path adjustment?)
            owd = round(geodesic(locations[node1_loc], locations[node2_loc]).meters * 1.1
                        / 200
                        + 1000)
        out.write('containerlab tools netem set -n {node} -i {iface} --delay {delay}\n'.format(
            node = src,
            iface = 'et-0/0/' + str(get_if_index(src,
                                                 fd_graph[src][dst]['interface'],
                                                 fd_graph)),
            delay = str(owd) + "us"))

if __name__ == '__main__':
    usage = """%prog [options] INPUT OUTPUT"""
    parser = OptionParser(usage)
    parser.add_option('-k', '--kind',
                      default='juniper_vjunosrouter',
                      help='node type to use with containerlab e.g. juniper_vjunosrouter')
    parser.add_option('-i', '--image',
                      default='vrnetlab/juniper_vjunos-router:24.2R1-S2.5',
                      help='image to use with containerlab')
    parser.add_option('-d', '--delay',
                      action='store_true',
                      default=False,
                      help='provide geographical latencies to links')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
        sys.exit(1)
    inputfile = args[0]
    outputfile = args[1]

    fd_graph = parse_netmap_topo(inputfile)
    if not outputfile:
        parser.error('Output filename not given')
    output = open(outputfile, 'w')
    output_yaml(fd_graph.to_undirected(), fd_graph, options.image, options.kind, output)
    print('Containerlab topology generated into {file}.'.format(file=outputfile))

    if options.delay:
        cmd_output = open('delaycmd.txt', 'w')
        output_netem_commands(fd_graph.to_undirected(), fd_graph, cmd_output)
        print('Additional commands for netem delay adjustments generated into delaycmd.txt')
