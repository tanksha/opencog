/*
 * QuantitativePredicateModule.h
 *
 *  Created on: 31 Mar, 2015
 *      Author: misgana
 */

#ifndef QUANTITATIVEPREDICATEMODULE_H_
#define QUANTITATIVEPREDICATEMODULE_H_

#include <opencog/server/Module.h>

namespace opencog
{
class QuantitativePredicateModule: Module {
private:
    AtomSpace * as_;
    boost::signals2::connection add_atom_connection_;
    boost::signals2::connection remove_atom_connection_;
    /**
     * Returns the the upper and lower bound  set of a quantile
     *eg. if svd =[10,20,30,40,50,60,70,80,90,100] and we need quartile,it will return
     * [10,25,45,65,100]
     */
    vector<int> get_quantile_border(const vector<int>& svd, int qsize);
    /*
     *Updates the SchemaValueRecordLink with the given QuantitativeSchemaNode type
     */
    void update_svrl(const Handle& hsvrl);
public:
    QuantitativePredicateModule(CogServer&);
    virtual ~QuantitativePredicateModule();
    virtual void run();
    const char * id(void);
    virtual void init(void);

    //! Atom added events
    void add_atom_signal(const Handle&);
    void add_atom_signal_handler(const Handle&);

    //! Atom removed events
    void remove_atom_signal(const Handle&, const AttentionValuePtr&,
                            const AttentionValuePtr&);
    void remove_atom_signal_handler(const Handle&, const AttentionValuePtr&,
                                    const AttentionValuePtr&);
};
}

#endif /*QUANTITATIVEPREDICATEMODULE_H_ */
