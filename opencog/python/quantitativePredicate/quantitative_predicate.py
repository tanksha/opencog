from opencog.atomspace import AtomSpace, types, Atom, Handle, TruthValue, types
import opencog.cogserver
import zmq
from threading import Thread
import json
import math


class Start(opencog.cogserver.Request):
    summary = 'Start the quantitativePredicate Module'
    description = "Usage: quantitativePredicate.Start Start the quantitativePredicate module. the purpose of this module" \
                  " is to control the new quantitativePredicate Nodes .This module hooks up to  the atomspace " \
                  "data is insertions signal  so that it will update the concerned quantitativePredicate node's" \
                  " truth value,"
    SVDL_SIZE = 20
    QUANTILE = 10
    PERSONALITY = 10
    ZMQ_IP_ADDRESS = '127.0.0.1'
    ZMQ_PORT = '5563'
    execution_link = None

    def contains_qsn(self, execution_link):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the boolean result of the check
        """
        el_elements = self.atomspace.get_outgoing(execution_link.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return True
        return False

    def svrl_by_qsn(self, quantitative_scheme_node):
        """
        Checks if a SchemaValueRecordLink exists with a given type of QuantitativeSchemaNode and returns the svrl
        """
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
        el_elements = self.atomspace.get_outgoing(handle=el.h)
        for e in el_elements:
            if e.type == types.NumberNode:
                return e
        return None

    def update_svrl(self, quantitative_scheme_node):
        """
         Updates the SchemaValueRecordLink with the given QuantitativeSchemaNode type
        """
        #check if there is an svrl with the above qsn
        svrl = self.svrl_by_qsn(quantitative_scheme_node)
        #if exists
        if not (svrl is None):
        # if its not full
            svll = self.atomspace.get_outgoing(svrl.h)[1]
            svll_elements = self.atomspace.get_outgoing(svll.h)
            if len(svll_elements) < self.SVDL_SIZE:
            # get ref to elements,remove it, add the new on elements set,create a new svrl
                self.atomspace.remove(atom=svll, recursive=False)
                self.atomspace.remove(atom=svrl, recursive=False)
                value_nn_node = self.atomspace.add_node(t=types.NumberNode,
                                                        atom_name=self.nn_from_el(self.execution_link).name,
                                                        tv=TruthValue(0.0, 0.0),
                                                        prefixed=False)
                count_nn_node = self.atomspace.add_node(t=types.NumberNode, atom_name="1", tv=TruthValue(0.0, 0.0),
                                                        prefixed=False)
                svll_elements.append(value_nn_node)
                svll_elements.append(count_nn_node)
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, outgoing=svll_elements,
                                               tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink, outgoing=[quantitative_scheme_node, svll],
                                               tv=TruthValue(0.0, 0.0))
            else:
                v = float(self.nn_from_el(self.execution_link).name)
                n_i = 1
                v_i = 0
                closest_index = 0
                diff = 0
                for i in range(1, len(svll_elements), 2):
                    v_i_tmp = float(svll_elements[i].name)
                    if i == 1:
                        closest_index = i
                        diff = math.fabs(v_i_tmp - v)
                        n_i = svll_elements[i + 1]
                        v_i = v_i_tmp
                    else:
                        if math.fabs(v_i_tmp - v) < diff:
                            diff = math.fabs(v_i_tmp - v)
                            closest_index = i
                            n_i = svll_elements[i + 1]
                            v_i = v_i_tmp
                        else:
                            continue
                            # update the count and the value based on v_i_new = [v_i * n_i / (n_i +1)] + v / (n_i +1)
                            #  and n_i_new=n_i +1
                v_i_new = (v_i * n_i / (n_i + 1)) + v / (n_i + 1)
                n_i += 1
                value_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name=str(v_i_new),
                                                       tv=TruthValue(0.0, 0.0), prefixed=False)
                count_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name=str(n_i),
                                                       tv=TruthValue(0.0, 0.0), prefixed=False)
                self.atomspace.remove(atom=svll_elements[closest_index], recursive=False)
                self.atomspace.remove(atom=svll_elements[closest_index + 1], recursive=False)
                svll_elements.insert(closest_index, value_nn_new)
                svll_elements.insert(closest_index + 1, count_nn_new)
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, outgoing=svll_elements,
                                               tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordink, outgoing=[quantitative_scheme_node, svll],
                                               tv=TruthValue(0.0, 0.0))
        else:
        #create a new svrl with the new value
            value_nn_new = self.atomspace.add_node(t=types.NumberNode,
                                                   atom_name=self.nn_from_el(self.execution_link).name,
                                                   tv=TruthValue(0.0, 0.0), prefixed=False)
            count_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name="1",
                                                   tv=TruthValue(0.0, 0.0), prefixed=False)
            svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink,
                                           outgoing=[quantitative_scheme_node, value_nn_new, count_nn_new],
                                           tv=TruthValue(0.0, 0.0))

    def qsn_from_el(self, el):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the QuantitativeSchemaNode
        """
        el_elements = self.atomspace.get_outgoing(el.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return e
        return None

    def el_by_qsn(self, qsn):
        """
        Returns an ExecutionLink with that contains a given QuantitativeSchemaNode
        """
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
        el_elements = self.atomspace.get_outgoing(handle=el.h)
        for e in el_elements:
            if e.type == types.ConceptNode:
                return e
        return None

    def get_svd(self, svrl):
        """
         Returns a sorted list of values in the SchemaValueRecordLink provided
        """
        svd = []
        svll = self.atomspace.get_outgoing(svrl.h)[1]
        svll_elements = self.atomspace.get_outgoing(svll.h)
        for i in range(1, len(svll_elements), 2):
            multiplicity = int(svll_elements[i + 1])
            for j in range(0, len(multiplicity)):
                svd.append(float(svll_elements[i].name))
        svd.sort()
        return svd

    def quantile_borders(self, svd):
        """
        Returns the the upper and lower bound set of a quantile
        eg. if svd =[10,20,30,40,50,60,70,80,90,100] and we need quartile,it will return
        [10,30,60,90,100]
        """
        # remainder is left since operands are integers
        qsize = len(svd) / self.QUANTILE
        quantile_border = []
        for i in range(0, len(svd), qsize):
            quantile_border.append(svd[i])
            #if svd is even, add the last one
        if len(svd) % qsize == 0:
            quantile_border.append(svd[len(svd) - 1])
        return quantile_border

    def qpn_of_qsn(self, quantitative_schema_node):
        """
        Returns a QuantitativePredicateNode with an identical Name as the QuantitativeSchemaNode
        """
        all_qpn = self.atomspace.get_atoms_by_type(t=types.QuantitativePredicateNode)
        for qpn in all_qpn:
            if qpn.name == quantitative_schema_node.name:
                return qpn
        return None

    def update_tv(self, quantitative_schema_node, qpn):
        """
         Update the truth values
        """
        #update the truth values as
        #el_list := get all el with the given QuantitativeSchemaNode type
        el_list = self.el_by_qsn(quantitative_schema_node)
        #svrl := get svrl with the given QuantitativeSchemaNode type
        svrl = self.svrl_by_qsn(quantitative_schema_node)
        #svd := quantize(svrl)
        svd = self.get_svd(svrl)
        border_values = self.quantile_borders(svd)
        #create EvaluationLink with p = [(element.value-lbound)*ubound_strength
        # + (ubound-element.value)*lbound_strength]/(ubound-lbound)
        for el in el_list:
            value_nn = self.nn_from_el(el)
            cn = self.cn_from_el(el)
            value = float(value_nn)
            p = None
            confidence = len(svd) / (len(svd) + self.PERSONALITY)
            q_size = len(border_values) - 1
            for i in range(0, len(border_values)):
                if value <= border_values[i]:
                    if i == 0:
                        p = 0
                    else:
                        p = ((value - border_values[i - 1]) * i / q_size) + (
                            (border_values[i] - value) * (i - 1) / q_size)
                    break
                else:
                    if i == len(border_values) - 1:
                        p = 1
                        break
        self.atomspace.add_link(t=types.EvaluationLink, [qpn, cn], tv=TruthValue(p, confidence))
    def run(self, args, atomspace):
        """
        Loads the REST API into a separate thread and invokes it,so that it will continue serving requests in the
        background after the Request that loads it has returned control to the CogServer
        """
        self.atomspace = atomspace
        print 'Greetings'
        thread = Thread(target=self.listener)
        thread.start()


    def listener(self):
        """
        A listener hooked to the atomspace for atom related events (here we listen for new ExecutionLink added events and validate
        that its related with a QuantitativeSchemaNode and update truth values of concerned Quantitative atoms)
        """
        print 'In module quantitative_predicate'
        context = zmq.Context(1)
        subscriber = context.socket(zmq.SUB)
        subscriber.connect('tcp://' + self.ZMQ_IP_ADDRESS + ':' + self.ZMQ_PORT)
        subscriber.setsockopt(zmq.SUBSCRIBE, 'add')
        #subscriber.setsockopt(zmq.SUBSCRIBE, 'remove')
        while True:
            [address, contents] = subscriber.recv_multipart()
            print '[%s]%s' % (address, contents)
            print "INFO:In while loop( listening to atom added)"
            atom = json.loads(contents)['atom']
            if address == 'add' and atom['type'] == 'ExecutionLink':
                self.execution_link = self.atomspace[Handle(int(atom['handle']))]
                if self.contains_qsn(self.execution_link):
                    qsn = self.qsn_from_el(self.execution_link)
                    #update SchemaValueRecordLink
                    self.update_svrl(qsn)
                    #check fo QuantitativePredicateNode with same name as QuantitativeSchemaNode
                    qpn = self.qpn_of_qsn(qsn)
                    if qpn is None:
                        qpn = self.atomspace.add_node(t=types.QuantitativeSchemaNode, atom_name=qsn.name,
                                                      tv=TruthValue(0.0, 0.0), prefixed=False)
                        #create a QuantitativeSchemaLink
                    self.atomspace.add_link(t=types.QuantitativePredicateLink, outgoing=[qpn, qsn],
                                            tv=TruthValue(0.0, 0.0))
                    svd = self.get_svd(self.svrl_by_qsn(qsn))
                     #if svd is  full
                    if len(svd) >= self.SVDL_SIZE:
                        self.update_tv(quantitative_schema_node=qsn, qpn=qpn)
                    subscriber.close()
                    context.term()

