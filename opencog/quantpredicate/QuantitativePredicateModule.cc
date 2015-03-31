/*
 * QuantitativePredicateModule.cc
 *
 * Copyright (C) 2015 by OpenCog Foundation
 * Written by Misgana Bayetta <misgana.bayetta@gmail.com>
 * All Rights Reserved
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License v3 as
 * published by the Free Software Foundation and including the exceptions
 * at http://opencog.org/wiki/Licenses
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program; if not, write to:
 * Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */
#include <opencog/server/CogServer.h>
#include <opencog/atomspace/AtomSpace.h>
#include <tbb/task.h>
#include <opencog/util/tbb.h>
#include <opencog/util/Config.h>
#include "QuantitativePredicateModule.h"

using namespace opencog;

DECLARE_MODULE(QuantitativePredicateModule);

QuantitativePredicateModule::QuantitativePredicateModule(CogServer& cs) :
        Module(cs)
{
    as_ = &cs.getAtomSpace();
    add_atom_connection_ = as_->addAtomSignal(
            boost::bind(&QuantitativePredicateModule::add_atom_signal, this,
                        _1));
    remove_atom_connection_ = as_->addAtomSignal(
            boost::bind(&QuantitativePredicateModule::remove_atom_connection_,
                        this, _1));
}

QuantitativePredicateModule::~PLNModule()
{
    logger().info("Destroying QuantitativePredicateModule instance.");
    add_atom_connection_.disconnect();
    remove_atom_connection_.disconnect();
}

void QuantitativePredicateModule::run()
{

}

void QuantitativePredicateModule::init()
{
    logger().info("Initializing QuantitativePredicateModule.");
}
/*
 * Create a task to handle the remove_atom_signal_handler event to avoid blocking.
 */
void QuantitativePredicateModule::remove_atom_signal(const Handle& source)
{
    tbb_enqueue_lambda([=] {
        remove_atom_signal_handler(source, av_old, av_new);
    });
}

/**
 * Update QSN when atom is remvoed
 */
void QuantitativePredicateModule::remove_atom_signal_handler(const Handle& h)
{

}
/*
 * Create a task to handle the add_atom_signal_handler event to avoid blocking.
 */
void QuantitativePredicateModule::add_atom_signal(const Handle& new_atom)
{
    tbb_enqueue_lambda([=] {
        add_atom_signal_handler(new_atom);
    });
}

/**
 * Whenever a new atom is added, start PLN reasoning.
 */
void QuantitativePredicateModule::add_atom_signal_handler(const Handle& h)
{

}

vector<int&> QuantitativePredicateModule::get_quantile_border(
        const vector<int>& svd, int qsize)
{

}

void QuantitativePredicateModule::update_svrl(const Handle& hsvrl)
{

}
