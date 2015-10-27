from opencog.atomspace import AtomSpace, types, Atom, Handle, TruthValue, types
import opencog.cogserver
import zmq
from threading import Thread
import json
import math
import logging
import pdb


class Start(opencog.cogserver.Request):
    summary = 'Start the quantitativePredicate Module'
    description = "Usage: quantitativePredicate.Start Start the quantitativePredicate module. the purpose of this module" \
                  " is listening to new quantitativePredicateNode insertion and change truth values of related atoms accordingly.This module hooks to" \
                  "atomspace signals.Atom insertion is the signal being listened so that this module updates the concerned quantitativePredicateNode's" \
                  " truth value,"
    SVDL_SIZE = 20
    QUANTILE = 10
    PERSONALITY = 10
    ZMQ_IP_ADDRESS = '127.0.0.1'
    ZMQ_PORT = '5563'
    execution_link = None

    def contains_qsn(self, execution_link):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the boolean result of the check operation.
        """
        logging.info("In contains_qsn-searching ExecutionLink by a given QuantitativeShemaNode")
        el_elements = self.atomspace.get_outgoing(execution_link.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return True
        return False

    def svrl_by_qsn(self, quantitative_scheme_node):
        """
        Checks if a SchemaValueRecordLink exists with a given type of QuantitativeSchemaNode and returns the svrl
        """
        logging.info("In svrl_by_qsn- searching SchemaValueRecordLink by a given QuantitativeShemaNode")
        svrl_list = self.atomspace.get_atoms_by_type(t=types.SchemaValueRecordLink)
        for svrl in svrl_list:
            svrl_elements = self.atomspace.get_outgoing(svrl.h)
            for e in svrl_elements:
                if e.type == types.QuantitativeSchemaNode:
                    return svrl
        return None

    def nn_from_el(self, el):
        """
        Returns the NumberNode in the ExecutionLink provided
        """
        logging.info("In nn_from_el-searching NumberNode in ExecutionLink")
        el_elements = self.atomspace.get_outgoing(el.h)
        for e in el_elements:
            if e.type == types.NumberNode:
                return e
        return None

    def update_svrl(self, quantitative_schema_node):
        """
         Updates the SchemaValueRecordLink with the given QuantitativeSchemaNode type
        """
        #check if there is an svrl with the above qsn
        logging.info("In update_svrl- updating content of the SchemaValueRecordLink of the QuantitativeSchemaNode")
        svrl = self.svrl_by_qsn(quantitative_schema_node)
        #if exists
        if not (svrl is None):
            svll = self.atomspace.get_outgoing(svrl.h)[1]
            svll_elements = self.atomspace.get_outgoing(svll.h)
            print "[DEBUG]:No of values in current SchemaValueRecordLink is %s" % str(len(svll_elements) / 2)
            # if its not full
            if len(svll_elements) / 2 < self.SVDL_SIZE:
                logging.info("\tAdding new value NumberNode")
                # get ref to elements,remove it, add the new on elements set,create a new svrl
                self.atomspace.remove(atom=svll, recursive=False)
                self.atomspace.remove(atom=svrl, recursive=False)
                value_nn_node = self.nn_from_el(self.execution_link)
                logging.info("\tAdding new count NumberNode")
                count_nn_node = self.atomspace.add_node(t=types.NumberNode, atom_name="1", tv=TruthValue(0.0, 0.0),
                                                        prefixed=False)
                # get ref to elements,remove it, add the new on elements set,create a new svrl
                #order of deletion of svrl and svll matters here
                self.atomspace.remove(atom=svrl, recursive=False)
                self.atomspace.remove(atom=svll, recursive=False)
                svll_elements.append(value_nn_node)
                svll_elements.append(count_nn_node)
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, outgoing=svll_elements,
                                               tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink, outgoing=[quantitative_schema_node, svll],
                                               tv=TruthValue(0.0, 0.0))

            else:
                logging.info("\tUpdating count and value NubmerNode")
                v = float(self.nn_from_el(self.execution_link).name)
                n_i = None
                v_i = None
                closest_index = None
                diff = None
                for i in range(0, len(svll_elements), 2):
                    v_i_tmp = float(svll_elements[i].name)
                    diff_tmp = math.fabs(v_i_tmp - v)
                    n_i_tmp = int(svll_elements[i + 1].name)
                    if i == 0:
                        closest_index = i
                        diff = math.fabs(v_i_tmp - v)
                        n_i = n_i_tmp
                        v_i = v_i_tmp
                    else:
                        if diff_tmp < diff:
                            diff = diff_tmp
                            closest_index = i
                            n_i = n_i_tmp
                            v_i = v_i_tmp
                            # update the count and the value based on v_i_new = [v_i * n_i / (n_i +1)] + v / (n_i +1)
                            #  and n_i_new=n_i +1
                v_i_new = (v_i * n_i / (n_i + 1)) + (v / (n_i + 1))
                n_i += 1
                value_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name=str(v_i_new),
                                                       tv=TruthValue(0.0, 0.0), prefixed=False)
                count_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name=str(n_i),
                                                       tv=TruthValue(0.0, 0.0), prefixed=False)
                #remove and recreate links and atoms
                #order of deletion of  matters here
                self.atomspace.remove(atom=svrl, recursive=False)
                self.atomspace.remove(atom=svll, recursive=False)
                self.atomspace.remove(atom=svll_elements[closest_index], recursive=False)
                #self.atomspace.remove(atom=svll_elements[closest_index + 1], recursive=False)
                del svll_elements[closest_index]
                #since element previously at i+1 becomes at i after single del operation
                del svll_elements[closest_index]

                svll_elements.insert(closest_index, value_nn_new)
                svll_elements.insert(closest_index + 1, count_nn_new)
                #print("SVLL:")
                #print svll_elements
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, outgoing=svll_elements,
                                               tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink, outgoing=[quantitative_schema_node, svll],
                                               tv=TruthValue(0.0, 0.0))
        else:
            logging.info("\tCreating a new SchemaValueListLink and SchemaValueRecordLink")
            #create a new svrl with the new value
            value_nn_new = self.nn_from_el(self.execution_link)
            count_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name="1",
                                                   tv=TruthValue(0.0, 0.0), prefixed=False)
            svll = self.atomspace.add_link(t=types.SchemaValueListLink,
                                           outgoing=[value_nn_new, count_nn_new],
                                           tv=TruthValue(0.0, 0.0))
            svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink,
                                           outgoing=[quantitative_schema_node, svll],
                                           tv=TruthValue(0.0, 0.0))
        print "[DEBUG]:svrl outgoing"
        print svrl

    def qsn_from_el(self, el):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the QuantitativeSchemaNode
        """
        logging.info("In qsn_from_el- Searching QuantitativeSchemaNode from ExecutionLink")
        el_elements = self.atomspace.get_outgoing(el.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return e
        return None

    def el_by_qsn(self, qsn):
        """
        Returns an ExecutionLink that contains a given QuantitativeSchemaNode
        """
        logging.info("In el_by_qsn- Searching ExecutionLink by QuantitativeSchemaNode")
        el_list = []
        all_el = self.atomspace.get_atoms_by_type(t=types.ExecutionLink)
        for e in all_el:
            outgoing = self.atomspace.get_outgoing(e.h)
            for o in outgoing:
                if o.h == qsn.h:
                    el_list.append(e)
                else:
                    continue
        return el_list

    def cn_from_el(self, el):
        """
        Returns the ConceptNode in the ExecutionLink provided
        """
        logging.info("In cn_from_el- searching for ConceptNode from ExecutionLink")
        el_elements = self.atomspace.get_outgoing(el.h)
        for e in el_elements:
            if e.type == types.ConceptNode:
                return e
        return None

    def get_svd(self, svrl):
        """
         Returns a sorted list of values in the SchemaValueRecordLink provided
        """
        logging.info("In get_svd - returning SchemaValueDistribution for a SchemaValueRecordLink")
        svd = []
        svrl_outgoing = self.atomspace.get_outgoing(svrl.h)
        logging.debug("\t SVRL_OUTGOING=")
        logging.debug(svrl_outgoing)
        svll = svrl_outgoing[1]
        svll_elements = self.atomspace.get_outgoing(svll.h)
        for i in range(0, len(svll_elements), 2):
            multiplicity = int(svll_elements[i + 1].name)
            for j in range(0, multiplicity):
                svd.append(float(svll_elements[i].name))
        svd.sort()
        return svd

    def quantile_borders(self, svd, q_size):
        """
        Returns the the upper and lower bound  set of a quantile
        eg. if svd =[10,20,30,40,50,60,70,80,90,100] and we need quartile,it will return
        [10,25,45,65,100]
        """
        logging.info("In quantile_borders- Calculating the quantile borders of a SchemaValueDistribution")
        # remainder is left since operands are integers
        qsize = len(svd) / q_size
        quantile_border = []
        remainder = len(svd) % q_size
        for i in range(0, len(svd), qsize):
            if i == 0:
                quantile_border.append(svd[i])
            else:
                if i + qsize >= len(svd) - 1:
                    if remainder == 0:
                        quantile_border.append((svd[i] + svd[i - 1]) / 2)
                    quantile_border.append(svd[len(svd) - 1])
                    break
                else:
                    quantile_border.append((svd[i] + svd[i - 1]) / 2)
        return quantile_border

    def qpn_of_qsn(self, quantitative_schema_node):
        """
        Returns a QuantitativePredicateNode with an identical Name as the QuantitativeSchemaNode
        """
        logging.info("In qpn_from_qsn- Searching for QuantitativePredicateNode from a QuantitativeSchemaNode")
        all_qpn = self.atomspace.get_atoms_by_type(t=types.QuantitativePredicateNode)
        for qpn in all_qpn:
            if qpn.name == quantitative_schema_node.name:
                return qpn
        return None

    def update_tv(self, quantitative_schema_node, qpn):
        """
         Update the truth values
        """
        logging.info("In update_tv- Updating truth value of")
        #update the truth values as
        #el_list := get all el with the given QuantitativeSchemaNode type
        el_list = self.el_by_qsn(quantitative_schema_node)
        #svrl := get svrl with the given QuantitativeSchemaNode type
        svrl = self.svrl_by_qsn(quantitative_schema_node)
        #svd := quantize(svrl)
        svd = self.get_svd(svrl)
        logging.debug("SVD=")
        logging.debug(svd)
        border_values = self.quantile_borders(svd, self.QUANTILE)
        logging.debug("SVD_BOUNDARY=")
        logging.debug(border_values)
        #create EvaluationLink with probability p = [(element.value-lbound)*ubound_strength
        # + (ubound-element.value)*lbound_strength]/(ubound-lbound)
        logging.info("Searching for related ExecutionLinks")
        for el in el_list:
            value_nn = self.nn_from_el(el)
            cn = self.cn_from_el(el)
            value = float(value_nn.name)
            p = None
            confidence = float(len(svd)) / (len(svd) + self.PERSONALITY)
            q_size = len(border_values) - 1
            for i in range(0, len(border_values)):
                if value <= border_values[i]:
                    if i == 0:
                        p = 0
                        break
                    else:
                        p = (((value - border_values[i - 1]) * i / q_size) + (
                            (border_values[i] - value) * (i - 1) / q_size)) / (border_values[i] - border_values[i - 1])
                        #logging.debug("setting p=" + str(p))
                        break
                else:
                    if i == len(border_values) - 1:
                        p = 1
                        break
            logging.debug("Evaluating  for %s with TV:(%s,%s)" % (cn.name, str(p), str(confidence)))
            self.atomspace.add_link(t=types.EvaluationLink, outgoing=[qpn, cn], tv=TruthValue(p, confidence))

    def run(self, args, atomspace):
        """
        Loads the REST API into a separate thread and invokes it,so that it will continue serving requests in the
        background after the Request that loads it has returned control to the CogServer
        """
        logging.root.setLevel(logging.DEBUG)
        logging.info("In run- Starting thread")
        self.atomspace = atomspace
        print 'Greetings'
        thread = Thread(target=self.listener)
        thread.start()


    def listener(self):
        """
        A listener hooked to the atomspace events (here we listen for new ExecutionLink added events and validate
        that its related with a QuantitativeSchemaNode and update truth values of concerned Quantitative atoms)
        """
        #print 'In module quantitative_predicate'
        logging.info("In listener- Listening for atom added")
        context = zmq.Context(1)
        subscriber = context.socket(zmq.SUB)
        subscriber.connect('tcp://' + self.ZMQ_IP_ADDRESS + ':' + self.ZMQ_PORT)
        subscriber.setsockopt(zmq.SUBSCRIBE, 'add')
        count = 0
        while True:
            logging.info("\tListening indefinitely in a while loop")
            test_list = subscriber.recv_multipart()
            if len(test_list) != 2:
                pdb.set_trace()
                logging.debug("LENGTH EXCEEDED 2.CONTETNT IS")
                for e in test_list:
                    print e
            [address, contents] = [test_list[0], test_list[1]]
            atom = json.loads(contents)['atom']
            if address == 'add' and atom['type'] == 'ExecutionLink':
                #print '[%s]%s' % (address, contents)
                logging.info("\tDetected and ExecutionLink added")
                count += 1
                logging.info("continuos insertion reached " + str(count))
                logging.info("\t Detected " + str(count) + " ExecutionLink insertions")
                self.execution_link = self.atomspace[Handle(int(atom['handle']))]
                if self.contains_qsn(self.execution_link):
                    logging.info("\tDetected ExecutionLink is related with QuantitativePredicate")
                    qsn = self.qsn_from_el(self.execution_link)
                    #update SchemaValueRecordLink
                    self.update_svrl(qsn)
                    #check fo QuantitativePredicateNode with same name as QuantitativeSchemaNode
                    qpn = self.qpn_of_qsn(qsn)
                    if qpn is None:
                        logging.info("\tCreating a new QuantitativePredicateNode")
                        qpn = self.atomspace.add_node(t=types.QuantitativePredicateNode, atom_name=qsn.name,
                                                      tv=TruthValue(0.0, 0.0), prefixed=False)
                        #create a QuantitativeSchemaLink
                    self.atomspace.add_link(t=types.QuantitativePredicateLink, outgoing=[qpn, qsn],
                                            tv=TruthValue(0.0, 0.0))
                    svd = self.get_svd(self.svrl_by_qsn(qsn))
                    if len(svd) > self.SVDL_SIZE:
                        logging.info("\tExecuting update truth value function")
                        self.update_tv(quantitative_schema_node=qsn, qpn=qpn)
        logging.info("\tClosing ZMQ subscriber")
        subscriber.close()
        context.term()
        logging.info("\tThread has been terminated")



