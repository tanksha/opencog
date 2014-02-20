#!/usr/bin/python2.7


__author__ = 'Misgana Bayetta'

import csv
import argparse
import os

#Nodes types used
STR_CN = 'ConceptNode'
STR_NN = 'NumberNode'
STR_QSN = 'QuantitativeSchemaNode'
STR_EL = 'ExecutionLink'

#change this if are going to generate any other quantitative predicate
PREDICATE = "GDP"


def get_gdp_matrix(inp_file):
    """
    array columns [code,country,GDP,rank]
	"""
    gdp_matrix = []
    fobject = open(inp_file, 'r')
    rows = csv.reader(fobject)
    gdp_list = list(rows)
    for i in range(0, len(gdp_list)):
        gdp_matrix.append(gdp_list[i])
    fobject.close()
    #test print
    #print "Country\tGPD"
    #print "-------\t---"
    #for row in gdp_matrix:
    #print row[3] + "\t" + row[4]
    #print row
    #exit(0)
    return gdp_matrix


def generate_scm_string(inp_file, out_file):
    """
     generates scm file for quantitative predicates
    """
    scm_begin = "("
    scm_end = ")"
    whole_scm = ""
    gdp_matrix = get_gdp_matrix(os.path.abspath(inp_file))
    for row in gdp_matrix:
        el = scm_begin + STR_EL + '\n'
        qsn = scm_begin + STR_QSN + '\t"' + PREDICATE + '"' + scm_end
        cn = scm_begin + STR_CN + '\t"' + row[2] + '"' + scm_end
        nn_value = scm_begin + STR_NN + '\t"' + row[3].replace(',', '') + '"' + scm_end
        el += qsn + '\n' + cn + '\n' + nn_value + '\n' + scm_end
        whole_scm += el + '\n'
    file_out = open(os.path.abspath(out_file), "wb")
    file_out.write(whole_scm)
    file_out.close()


if __name__ == "__main__":
    usage = "usage: %prog [options]\n"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("-i", "--input", nargs=1, help="The gdp list in csv file")
    parser.add_argument("-o", "--out", nargs=1, help="Scheme file write location")
    args = parser.parse_args()
    if args.input and args.out:
        print "started scheme file generation..."
        generate_scm_string(args.input[0], args.out[0])
        print "finished. file has been written to %s " % os.path.abspath(args.out[0])
    else:
        parser.print_help()




