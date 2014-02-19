from opencog.atomspace import AtomSpace, types, Atom, Handle, TruthValue, types
import opencog
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
    execution_link = None

    def contains_qsn(self, execution_link):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the boolean result of the check
        """
        el_elements = self.atomspace.get_outgoing(handle=execution_link.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return True
        return False

    def svrl_by_qsn(self, quantitative_scheme_node):
        """
        Checks if a SchemaValueRecordLink exists with a given type of QuantitativeSchemaNode and returns the svrl
        """
        svrl_list = self.atomspace.get_atoms_by_type(t=types.SchemavalueRecordLink)
        for svrl in svrl_list:
            svrl_elements = self.atomspace.get_outgoing(handle=svrl.h)
            for e in svrl_elements:
                if e.type == types.QuantitativeSchemanode:
                    return svrl
        return None

    def nn_from_el(self, el):
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
        if not (svrl is None):
        #if exists
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
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, svll_elements, tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink, [quantitative_scheme_node, svll],
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
                svll = self.atomspace.add_link(t=types.SchemaValueListLink, svll_elements, tv=TruthValue(0.0, 0.0))
                svrl = self.atomspace.add_link(t=types.SchemaValueRecordink, [quantitative_scheme_node, svll],
                                               tv=TruthValue(0.0, 0.0))
        else:
        #create a new svrl with the new value
            value_nn_new = self.atomspace.add_node(t=types.NumberNode,
                                                   atom_name=self.nn_from_el(self.execution_link).name,
                                                   tv=TruthValue(0.0, 0.0), prefixed=False)
            count_nn_new = self.atomspace.add_node(t=types.NumberNode, atom_name="1",
                                                   tv=TruthValue(0.0, 0.0), prefixed=False)
            svrl = self.atomspace.add_link(t=types.SchemaValueRecordLink,
                                           [quantitative_scheme_node, value_nn_new, count_nn_new],
                                           tv=TruthValue(0.0, 0.0))

    def qsn_from_el(self, el):
        """
         Checks whether the ExecutionLink is related with QuantitativeSchemaNode or not and returns the QuantitativeSchemaNode
        """
        el_elements = self.atomspace.get_outgoing(handle=el.h)
        for e in el_elements:
            if e.type == types.QuantitativeSchemaNode:
                return e
        return None

    def el_by_qsn(self, qsn):
        el_list = []
        all_el = self.atomspace.get_atoms_by_type(t=types.ExecutionLink)
        for e in all_el:
            outgoing = self.atomspace.get_outgoing(handle=e.h)
            for o in outgoing:
                if o.h == qsn.h:
                    el_list.append(e)
                else:
                    continue
        return el_list

    def cn_from_el(self, el):
        el_elements = self.atomspace.get_outgoing(handle=el.h)
        for e in el_elements:
            if e.type == types.ConceptNode:
                return e
        return None

    def quantile_borders(self, svrl):
        """
        Returns the the upper and lower bound set of a quantile
        eg. if svd =[10,20,30,40,50,60,70,80,90,100] and we need quartile,it will return
        [10,30,60,90,100]
        """
        svd = []
        svll = self.atomspace.get_outgoing(handle=svrl.h)[1]
        svll_elements = self.atomspace.get_outgoing(handle=svll.h)
        for i in range(1, len(svll_elements), 2):
            multiplicity = int(svll_elements[i + 1])
            for j in range(0, len(multiplicity)):
                svd.append(float(svll_elements[i].name))
        svd.sort()
        # remainder is left since operands are integers
        qsize = len(svd) / self.QUANTILE
        quantile_border = []
        for i in range(0, svd, qsize):
            quantile_border.append(svd[i])
            #if svd is even, add the last one
        if len(svd) % qsize == 0:
            quantile_border.append(svd[len(svd) - 1])
        return quantile_border

    def update_tv(self, quantitative_schema_node):
        """
         Update the truth values
        """
        #update the truth values as
        #el_list := get all el with the given QuantitativeSchemaNode type
        el_list = self.el_by_qsn(quantitative_schema_node)
        #svrl := get svrl with the given QuantitativeSchemaNode type
        svrl = self.svrl_by_qsn(quantitative_schema_node)
        #svd := quantize(svrl)
        border_values = self.quantile_borders(svrl)
        for el in el_list:
            value_nn = self.nn_from_el(el)
            cn = self.cn_from_el(el)
            value = float(value_nn)
            for i in range(0,border_values):
                if value < border_values[i]:
                    ubound=border_values[i]
            #create EvaluationLink with p = [(element.value-lbound)*ubound_strength
        # + (ubound-element.value)*lbound_strength]/(ubound-lbound)


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
        print 'In module quantitative_predicate'
        context = zmq.Context(1)
        subscriber = context.socket(zmq.SUB)
        subscriber.connect('tcp://' + zmq.ZMQ_IP_ADDRESS + ':' + zmq.ZMQ_PORT)
        subscriber.setsockopt(zmq.SUBSCRIBE, 'add')
        subscriber.setsockopt(zmq.SUBSCRIBE, 'remove')
        while True:
            address, contents = subscriber.recv_multipart()
            print '[%s]%s' % (address, contents)
            atom = json.loads(contents)['atoms']
            if address == 'add' and atom['type'] == 'ExecutionLink':
                self.execution_link = self.atomspace[Handle(atom['handle'])]
                if self.contains_qsn(self.execution_link):
                    #update SchemaValueRecordLink
                    self.update_svrl(self.qsn_from_el(self.execution_link))
                    self.update_tv(self.qsn_from_el(self.execution_link))
                    #update truth value
                    pass
            subscriber.close()
            context.term()





