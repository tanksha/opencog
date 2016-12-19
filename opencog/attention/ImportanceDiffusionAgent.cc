/*
 * opencog/attention/ImportanceDiffusionAgent.cc
 *
 * Copyright (C) 2008 by OpenCog Foundation
 * Written by Joel Pitt <joel@fruitionnz.com>
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

#include <time.h>
#include <math.h>

#include <opencog/util/Config.h>
#include <opencog/util/platform.h>
#include <opencog/util/mt19937ar.h>

#include <opencog/atoms/base/Link.h>
#include <opencog/attention/atom_types.h>

#include <opencog/atomspace/AtomSpace.h>
#include <opencog/cogserver/server/CogServer.h>

#include "ImportanceDiffusionAgent.h"

#define DEBUG
namespace opencog
{

ImportanceDiffusionAgent::ImportanceDiffusionAgent(CogServer& cs) :
    Agent(cs)
{
    setParameters({
        //! Default value that normalised STI has to be above before
        //! being spread
        "ECAN_DIFFUSION_THRESHOLD","0.0",
        //! Maximum percentage of STI that is spread from an atom
        "ECAN_MAX_SPREAD_PERCENTAGE","1.0",
        "ECAN_ALL_LINKS_SPREAD","false",
        "",""
    });
    spreadDecider = NULL;

    //! @todo won't respond to the parameters being changed later
    //! (not a problem at present, but could get awkward with, for example,
    //! automatic parameter adaptation)
    maxSpreadPercentage = config().get_double("ECAN_MAX_SPREAD_PERCENTAGE");

    setSpreadDecider(STEP);
    setDiffusionThreshold(config().get_double("ECAN_DIFFUSION_THRESHOLD"));

    allLinksSpread = config().get_bool("ECAN_ALL_LINKS_SPREAD");

    // Provide a logger
    setLogger(new opencog::Logger("ImportanceDiffusionAgent.log", Logger::FINE, true));
}

void ImportanceDiffusionAgent::setSpreadDecider(int type, double shape)
{
    if (spreadDecider) {
        delete spreadDecider;
        spreadDecider = NULL;
    }
    switch (type) {
    case HYPERBOLIC:
        spreadDecider = (SpreadDecider*) new HyperbolicDecider(_cogserver, shape);
        break;
    case STEP:
        spreadDecider = (SpreadDecider*) new StepDecider(_cogserver);
        break;
    }

}

ImportanceDiffusionAgent::~ImportanceDiffusionAgent()
{
    if (spreadDecider) {
        delete spreadDecider;
        spreadDecider = NULL;
    }
}

void ImportanceDiffusionAgent::setMaxSpreadPercentage(double p)
{ maxSpreadPercentage = p; }

double ImportanceDiffusionAgent::getMaxSpreadPercentage() const
{ return maxSpreadPercentage; }

void ImportanceDiffusionAgent::setDiffusionThreshold(double p)
{
    diffusionThreshold = p;
}

double ImportanceDiffusionAgent::getDiffusionThreshold() const
{ return diffusionThreshold; }

void ImportanceDiffusionAgent::run()
{
    spreadDecider->setFocusBoundary(diffusionThreshold);
#ifdef DEBUG
    totalSTI = 0;
#endif
    spreadImportance();
}

#define toFloat getMean

int ImportanceDiffusionAgent::makeDiffusionAtomsMap(std::map<Handle,int> &diffusionAtomsMap,
        HandleSeq links)
{
    int totalDiffusionAtoms = 0;
    HandleSeq::iterator hi;

#ifdef DEBUG
    _log->fine("Finding atoms involved with STI diffusion and their matrix indices");
#endif
    for (hi = links.begin(); hi != links.end(); ++hi) {
        // Get all atoms in outgoing set of links
        HandleSeq targets;
        HandleSeq::iterator targetItr;
        Handle linkHandle = *hi;
        double val = linkHandle->getTruthValue()->toFloat();
        if (val == 0.0) {
            continue;
        }

        targets = linkHandle->getOutgoingSet();

        for (targetItr = targets.begin(); targetItr != targets.end();
                ++targetItr)
        {
            if (diffusionAtomsMap.find(*targetItr) == diffusionAtomsMap.end())
            {
                diffusionAtomsMap[*targetItr] = totalDiffusionAtoms;
#ifdef DEBUG
                _log->fine("%s = %d", (*targetItr)->toString().c_str(),
                        totalDiffusionAtoms);
#endif
                totalDiffusionAtoms++;
            }
        }
    }
    // diffusionAtomsMap now contains all atoms involved in spread as keys and
    // their matrix indices as values.
    return totalDiffusionAtoms;
}

void ImportanceDiffusionAgent::makeSTIVector(bvector* &stiVector,
        int totalDiffusionAtoms, std::map<Handle,int> diffusionAtomsMap) {
    // go through diffusionAtomsMap and add each to the STI vector.
    // position in stiVector matches set (set is ordered and won't change
    // unless you add to it.
    // alloc
    stiVector = new bvector(totalDiffusionAtoms);
    // zero vector
    //gsl_vector_set_zero(stiVector);

    for (std::map<Handle,int>::iterator i=diffusionAtomsMap.begin();
            i != diffusionAtomsMap.end(); ++i) {
        Handle dAtom = (*i).first;
// For some reason I thought linearising -ve and +ve separately might
// be a good idea, but this messes up the conservation of STI
//      (*stiVector)((*i).second) = _as->getNormalisedSTI(dAtom,false)+1.0)/2.0);
        (*stiVector)((*i).second) = _as->get_normalised_zero_to_one_STI(dAtom,false);
#ifdef DEBUG
        totalSTI += dAtom->getSTI();
#endif
    }

#ifdef DEBUG
    if (_log->is_fine_enabled()) {
        _log->fine("Initial normalised STI values");
        printVector(stiVector);
    }
#endif
}

void ImportanceDiffusionAgent::makeConnectionMatrix(bmatrix* &connections_,
        int totalDiffusionAtoms, std::map<Handle,int> diffusionAtomsMap,
        HandleSeq links)
{
    HandleSeq::iterator hi;
    // set connectivity matrix size, size is dependent on the number of atoms
    // that are connected by a HebbianLink in some way.
//    connections = gsl_matrix_alloc(totalDiffusionAtoms, totalDiffusionAtoms);
    connections_ = new bmatrix(totalDiffusionAtoms, totalDiffusionAtoms, totalDiffusionAtoms * totalDiffusionAtoms);
    // To avoid having to dereference pointers everywhere
    bmatrix& connections = *connections_;

    for (hi=links.begin(); hi != links.end(); ++hi)
    {
        // Get all atoms in outgoing set of link
        HandleSeq targets;
        HandleSeq::iterator targetItr;

        std::map<Handle,int>::iterator sourcePosItr;
        std::map<Handle,int>::iterator targetPosItr;
        int sourceIndex;
        int targetIndex;
        Type type;

        double val = (*hi)->getTruthValue()->toFloat();
        if (val == 0.0) continue;
        //val *= diffuseTemperature;
        type = (*hi)->getType();

        targets = (*hi)->getOutgoingSet();
        if (classserver().isA(type,ORDERED_LINK)) {
            Handle sourceHandle;

            // Add only the source index
            sourcePosItr = diffusionAtomsMap.find(targets[0]);
#ifdef DEBUG
            if (sourcePosItr == diffusionAtomsMap.end()) {
                // This case should never occur
                _log->warn("Can't find source in list of diffusionNodes. "
                        "Something odd has happened");
            }
#endif
            sourceHandle = (*sourcePosItr).first;
            // If source atom isn't within diffusionThreshold, then skip
            if (!spreadDecider->spreadDecision(sourceHandle->getSTI())) {
                continue;
            }
            sourceIndex = (*sourcePosItr).second;
#ifdef DEBUG
            _log->fine("Ordered link with source index %d.", sourceIndex);
#endif
            // Then spread from index 1 (since source is at index 0)

            targetItr = targets.begin();
            ++targetItr;
            for (; targetItr != targets.end();
            //for (targetItr = (targets.begin())++; targetItr != targets.end();
                     ++targetItr) {
                targetPosItr = diffusionAtomsMap.find(*targetItr);
                targetIndex = (*targetPosItr).second;
                if (type == INVERSE_HEBBIAN_LINK) {
                    // source and target indices swapped because inverse
                    //gsl_matrix_set(connections,sourceIndex,targetIndex,val);
                    connections(sourceIndex,targetIndex) += val;
                } else {
                    //gsl_matrix_set(connections,targetIndex,sourceIndex,val);
                    connections(targetIndex,sourceIndex) += val;
                }
            }
        } else {
            HandleSeq::iterator sourceItr;
            // Add the indices of all targets as sources
            // then go through all pairwise combinations
#ifdef DEBUG
            _log->fine("Unordered link");
#endif
            for (sourceItr = targets.begin(); sourceItr != targets.end();
                    ++sourceItr) {
                Handle sourceHandle;
                sourceHandle = (*sourceItr);
                // If source atom isn't within diffusionThreshold, then skip
                if (!spreadDecider->spreadDecision(sourceHandle->getSTI())) {
                    continue;
                }
                for (targetItr = targets.begin(); targetItr != targets.end();
                        ++targetItr) {
                    if (*targetItr == *sourceItr) continue;
                    sourcePosItr = diffusionAtomsMap.find(*sourceItr);
                    sourceIndex = (*sourcePosItr).second;
                    targetPosItr = diffusionAtomsMap.find(*targetItr);
                    targetIndex = (*targetPosItr).second;
                    if (type == SYMMETRIC_INVERSE_HEBBIAN_LINK) {
                        connections(sourceIndex,targetIndex) += val;
                    } else {
                        connections(targetIndex,sourceIndex) += val;
                    }
                }
            }
        }
    }
    // Make sure columns sum to 1.0 and that no more than maxSpreadPercentage
    // is taken from source atoms
#ifdef DEBUG
    _log->fine("Sum probability for column:");
#endif
    for (unsigned int j = 0; j < connections.size2(); j++) {
        double sumProb = 0.0;
        for (unsigned int i = 0; i < connections.size1(); i++) {
            if (i != j) sumProb += connections(i,j);
        }
#ifdef DEBUG
        _log->fine("%d before - %1.3f", j, sumProb);
#endif

        if (sumProb > maxSpreadPercentage) {
            for (unsigned int i = 0; i < connections.size1(); i++) {
                connections(i,j) = connections(i,j)
                        / (sumProb/maxSpreadPercentage) ;
            }
            sumProb = maxSpreadPercentage;
        }
#ifdef DEBUG
        _log->fine("%d after - %1.3f", j, sumProb);
#endif
        //gsl_matrix_set(connections,j,j,1.0-sumProb);
        connections(j,j) = 1.0-sumProb;
    }

#ifdef DEBUG
    if (_log->is_fine_enabled()) {
        _log->debug("Hebbian connection matrix:");
        printMatrix(connections_);
    }
#endif
}

void ImportanceDiffusionAgent::spreadImportance()
{
    bmatrix* connections;
    bvector* stiVector;
//    bvector* result;
//    int errorNo;

    // The source and destinations of STI
    std::map<Handle,int> diffusionAtomsMap;
    int totalDiffusionAtoms = 0;

    HandleSeq links;
    std::back_insert_iterator<HandleSeq> out_hi(links);

    _log->debug("Begin diffusive importance spread.");

    // Get all HebbianLinks
    if (allLinksSpread) {
      _as->get_handles_by_type(out_hi, LINK, true);
    } else {
      _as->get_handles_by_type(out_hi, HEBBIAN_LINK, true);
    }

    totalDiffusionAtoms = makeDiffusionAtomsMap(diffusionAtomsMap, links);

    // No Hebbian Links or atoms?
    if (totalDiffusionAtoms == 0) { return; }

#ifdef DEBUG
    _log->debug("%d total diffusion atoms.", totalDiffusionAtoms);
    _log->fine("Creating normalized STI vector.");
#endif

    makeSTIVector(stiVector,totalDiffusionAtoms,diffusionAtomsMap);

    makeConnectionMatrix(connections, totalDiffusionAtoms, diffusionAtomsMap, links);

    bvector result = prod(*connections, *stiVector);

    if (_log->is_fine_enabled()) {
        double normAF = (_as->get_attentional_focus_boundary() - _as->get_min_STI(false)) / (double) ( _as->get_max_STI(false) - _as->get_min_STI(false) );
        _log->fine("Result (AF at %.3f)\n",normAF);
        printVector(&result, normAF);
    }

    // set the sti of all atoms based on new values in results vector from
    // multiplication
#ifdef DEBUG
    int totalSTI_After = 0;
#endif
    for (std::map<Handle,int>::iterator i=diffusionAtomsMap.begin();
            i != diffusionAtomsMap.end(); ++i)
    {
        Handle dAtom = i->first;
        double val = result(i->second);
        setScaledSTI(dAtom, val);
#ifdef DEBUG
        totalSTI_After += dAtom->getSTI();
#endif
    }
#if 0 //def DEBUG
    if (totalSTI != totalSTI_After) {
        // This warning is often logged because of doubleing point round offs
        // when converting from normalised to actual STI values after diffusion.
        log->warn("Total STI before diffusion (%d) != Total STI after (%d)",totalSTI,totalSTI_After);
    }
#endif

    // free memory!
    delete connections;
    delete stiVector;
}

void ImportanceDiffusionAgent::setScaledSTI(Handle h, double scaledSTI)
{
    AttentionValue::sti_t val;

    val = (AttentionValue::sti_t) (_as->get_min_STI(false) + (scaledSTI * ( _as->get_max_STI(false) - _as->get_min_STI(false) )));
/*
    double af = _as->getAttentionalFocusBoundary();
    scaledSTI = (scaledSTI * 2) - 1;
    if (scaledSTI <= 1.0) {
        val = _as->getMinSTI(false) + (scaledSTI * ( _as->getMinSTI(false) - af ));
    } else {
        val = af + (scaledSTI * (_as->getMaxSTI(false) - af ));
    }
*/
    h->setSTI(val);
}

void ImportanceDiffusionAgent::printMatrix(bmatrix* m)
{
    typedef boost::numeric::ublas::compressed_matrix<double>::iterator1 it1_t;
    typedef boost::numeric::ublas::compressed_matrix<double>::iterator2 it2_t;

    for (it1_t it1 = m->begin1(); it1 != m->end1(); it1++) {
        for (it2_t it2 = it1.begin(); it2 != it1.end(); it2++) {
            _log->fine("(%d,%d) %f", it2.index1(), it2.index2(), *it2);
        }
    }
}

void ImportanceDiffusionAgent::printVector(bvector* v, double threshold)
{
    typedef boost::numeric::ublas::vector<double>::iterator it_t;

    for (it_t it = v->begin(); it != v->end(); ++it) {
        if (*it > threshold) {
            _log->fine("(%d) %f +", it.index(), *it);
        }
        else {
            _log->fine("(%d) %f", it.index(), *it);
        }
    }
}

// Static/Shared random number generator
RandGen* SpreadDecider::rng = NULL;

bool SpreadDecider::spreadDecision(AttentionValue::sti_t s)
{
    if (getRNG()->randdouble() < function(s))
        return true;
    else
        return false;
}

RandGen* SpreadDecider::getRNG()
{
    if (!rng)
        rng = new opencog::MT19937RandGen((unsigned long) time(NULL));
    return rng;
}

double HyperbolicDecider::function(AttentionValue::sti_t s)
{
    AtomSpace& a = _cogserver.getAtomSpace();
    // Convert boundary from -1..1 to 0..1
    double af = a.get_attentional_focus_boundary();
    double minSTI = a.get_min_STI(false);
    double maxSTI = a.get_max_STI(false);
    double norm_b = focusBoundary > 0.0 ?
        af + (focusBoundary * (maxSTI - af)) :
        af + (focusBoundary * (af - minSTI ));
    // norm_b is now the actual STI value, normalise to 0..1
    norm_b = (norm_b - minSTI) / (double) ( maxSTI - minSTI );
    // Scale s to 0..1
    double norm_s = (s - minSTI) / (double) ( maxSTI - minSTI );
    return (tanh(shape*(norm_s-norm_b))+1.0)/2.0;
}

void HyperbolicDecider::setFocusBoundary(double b)
{
    // Store as -1..1 since exact 0..1 mapping of boundary
    // will change based on min/max STI
    focusBoundary = b;
}

double StepDecider::function(AttentionValue::sti_t s)
{
    return (s>focusBoundary ? 1.0 : 0.0);
}

void StepDecider::setFocusBoundary(double b)
{
    AtomSpace& a = _cogserver.getAtomSpace();
    // Convert to an exact STI amount
    double af = a.get_attentional_focus_boundary();
    focusBoundary = (b > 0.0)?
        (int) (af + (b * (a.get_max_STI(false) - af))) :
        (int) (af + (b * (af - a.get_min_STI(false))));

}

};

