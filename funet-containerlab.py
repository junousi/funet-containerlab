#!/usr/bin/env python3

import sys
import networkx as nx
import re
from operator import itemgetter
from optparse import OptionParser

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
                m1 = re.match(r"<!-- ([a-z0-9]+.ip.funet.fi)", line)
                if m1 != None:
                    src = m1.group(1)
                    g.add_node(src)
                m2 = re.match(r".* ([a-z0-9]+.ip.funet.fi) -->", line)
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

def output_yaml(hd_graph, fd_graph):
    """
    Output a containerlab-compatible topology to stdout.
    """
    print('''---
name: funet-containerlab
mgmt:
  bridge: virbr0
  ipv4-subnet: 192.168.42.0/24
topology:''')
    print('  nodes:')
    for index,n in enumerate(hd_graph.nodes):
        print('''    {router}:
      kind: juniper_vjunosrouter
      image: vrnetlab/juniper_vjunos-router:23.2R1.15
      mgmt-ipv4: 192.168.42.{index}
      startup-config: {router}.cfg'''.format(router=n, index=index+100))
    print('  links:')
    # The source HTML does not contain full-duplex interface data, thus we
    # need to work with two graphs; one that holds the half-duplex links wanted
    # by containerlab topology parser, and the other which has awareness of the
    # specific router interface for B in the case of A->B.
    for src, dst, dummyif in hd_graph.edges.data():
        print('    - endpoints: ["{rtr1}:{if1}", "{rtr2}:{if2}"]'.format( \
            rtr1 = src,
            if1  = 'et-0/0/' + str(get_if_index(src,
                                                fd_graph[src][dst]['interface'],
                                                fd_graph)),
            rtr2 = dst,
            if2  = 'et-0/0/' + str(get_if_index(dst,
                                                fd_graph[dst][src]['interface'],
                                                fd_graph))))

if __name__ == '__main__':
    usage = """%prog [options] topofile.html"""
    parser = OptionParser(usage)
#TODO
#    parser.add_option('-o', '--output', dest='output',
#                      help='Output file, if omitted stdout')
#TODO Proper src/ structure might be nice as well.
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(1)
    fd_graph = parse_netmap_topo(args[0])
    output_yaml(fd_graph.to_undirected(), fd_graph)
