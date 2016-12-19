/*
 * opencog/attention/ImportanceSpreadingAgent.cc
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

#include <opencog/util/Config.h>
#include <opencog/util/platform.h>

#include <opencog/atoms/base/Link.h>
#include <opencog/attention/atom_types.h>

#include <opencog/atomspace/AtomSpace.h>

#include <opencog/cogserver/server/CogServer.h>

#include "ImportanceSpreadingAgent.h"

using namespace opencog;

ImportanceSpreadingAgent::ImportanceSpreadingAgent(CogServer& cs) :
    Agent(cs)
{
    setParameters({
        "ECAN_DEFAULT_SPREAD_THRESHOLD","0",
        "ECAN_DEFAULT_SPREAD_MULTIPLIER","10.0",
        "ECAN_ALL_LINKS_SPREAD","false",
        "", ""
    });

    spreadThreshold = config().get_double("ECAN_DEFAULT_SPREAD_THRESHOLD");
    allLinksSpread = config().get_bool("ECAN_ALL_LINKS_SPREAD");

    // Provide a logger
    setLogger(new opencog::Logger("ImportanceSpreadingAgent.log", Logger::FINE, true));
}

ImportanceSpreadingAgent::~ImportanceSpreadingAgent()
{
}

void ImportanceSpreadingAgent::run()
{
    spreadImportance();
}


void ImportanceSpreadingAgent::spreadImportance()
{
    AttentionValue::sti_t current;

    HandleSeq atoms;
    HandleSeq::iterator hi;
    std::back_insert_iterator<HandleSeq> out_hi(atoms);

    _as->get_handles_by_type(out_hi, NODE, true);
   _log->fine("---------- Spreading importance for atoms with threshold above %d", spreadThreshold);

    hi = atoms.begin();
    while (hi != atoms.end()) {
        Handle h = *hi;

        current = h->getSTI();
        // spread if STI > spread threshold
        if (current > spreadThreshold )
            // spread fraction of importance to nodes it's linked to
            spreadAtomImportance(h);

        ++hi;
    }
}

// for a bunch of links from the source, get links passed as pointer
// to avoid retrieving them twice
int ImportanceSpreadingAgent::sumTotalDifference(Handle source, HandleSeq& links)
{
    int totalDifference = 0;
    // sum total difference
    for (Handle handle : links) {
        totalDifference += sumDifference(source,handle);
    }
    return totalDifference;
}

static bool is_source(const Handle& source, const Handle& link)
{
    LinkPtr lptr(LinkCast(link));
    // On ordered links, only the first position in the outgoing set
    // is a source of this link. So, if the handle given is equal to
    // the first position, true is returned.
    Arity arity = lptr->getArity();
    if (classserver().isA(lptr->getType(), ORDERED_LINK)) {
        return arity > 0 and lptr->getOutgoingAtom(0) == source;
    } else if (classserver().isA(lptr->getType(), UNORDERED_LINK)) {
        // If the link is unordered, the outgoing set is scanned;
        // return true if any position is equal to the source.
        for (const Handle& h : lptr->getOutgoingSet())
            if (h == source) return true;
        return false;
    }
    return false;
}


#define toFloat getMean
// For one link
int ImportanceSpreadingAgent::sumDifference(Handle source, Handle link)
{
    double linkWeight;
    double linkDifference = 0.0;
    HandleSeq targets;
    HandleSeq::iterator t;
    AttentionValue::sti_t sourceSTI;
    AttentionValue::sti_t targetSTI;

    // If this link doesn't have source as a source return 0
    if (! is_source(source, link)) {
       _log->debug("Skipping link because link doesn't have this source as a source: " + link->toString());
        return 0;
    }

    // Get outgoing set and sum difference for all non source atoms
    linkWeight = link->getTruthValue()->toFloat();
    sourceSTI = source->getSTI();
    targets = link->getOutgoingSet();

    if (link->getType() == INVERSE_HEBBIAN_LINK)
    {
        for (t = targets.begin(); t != targets.end(); ++t) {
            Handle target_h = *t;
            if (target_h == source) continue;
            targetSTI = target_h->getSTI();

            // pylab code for playing with inverse link stealing schemes:
            // s=10; w=0.5; t= frange(-20,20,0.05x)
            // plot(t,[max(y,0)*s*w for y in log([max(x,0.000001) for x in t+(s*w)])])
            // plot(t,[max(x,0) for x in w*(t+(w*s))])
            // plot(t,[max(min(x,w*s),0) for x in w/2*t+(w*w*s)])
            // ... using this last one.
            linkDifference += calcInverseDifference(sourceSTI, targetSTI, linkWeight);
        }
    } else {
        for (t = targets.begin(); t != targets.end(); ++t) {
            Handle target_h = *t;

            if (target_h == source) {
               _log->debug("Skipping link because link has source as target: " + link->toString());
                continue;
            }

           _log->fine("Target atom %s", target_h->toString().c_str());

            targetSTI = target_h->getSTI();  // why is it 0?

            linkDifference += calcDifference(sourceSTI, targetSTI, linkWeight);
        }
    }
    if (link->getType() == INVERSE_HEBBIAN_LINK) {
        linkDifference *= -1.0;
    }
    return (int) linkDifference;
}

double ImportanceSpreadingAgent::calcInverseDifference(AttentionValue::sti_t s, AttentionValue::sti_t t, double weight)
{
    double amount;
    amount = weight * t + (weight * weight * s);
    if (amount < 0) amount = 0;
    else if (amount > weight * s) amount = weight * s;
    return amount;
}

double ImportanceSpreadingAgent::calcDifference(AttentionValue::sti_t s, AttentionValue::sti_t t, double weight)
{
    // importance can't spread uphill
    if (s - t > 0) {
        return weight * (s - t);
    }
    return 0.0;
}

bool ImportanceSpreadingAgent::IsHebbianLink::operator()(Handle h)
{
    if (classserver().isA(h->getType(), HEBBIAN_LINK)) return true;
    return false;
}

void ImportanceSpreadingAgent::spreadAtomImportance(Handle h)
{
    HandleSeq links;
    double totalDifference, differenceScaling;
    AttentionValue::sti_t sourceSTI;

    HandleSeq linksVector;
    HandleSeq::iterator linksVector_i;

    totalDifference = 0.0;
    differenceScaling = 1.0;

    _log->fine("+Spreading importance for atom %s", h->toString().c_str());

    h->getIncomingSet(back_inserter(linksVector));
    IsHebbianLink isHLPred(_as);
    if (allLinksSpread) {
       _log->fine("  +Spreading across all links. Found %d", linksVector.size());
    } else {
      linksVector.erase(std::remove_if(linksVector.begin(), linksVector.end(), isHLPred), linksVector.end());
      _log->fine("  +Hebbian links found %d", linksVector.size());
    }

    totalDifference = sumTotalDifference(h, linksVector);
    sourceSTI = h->getSTI();

    // if there is no hebbian links with > 0 weight
    // or no lower STI atoms to spread to.
    if (totalDifference == 0.0) {
       _log->fine("  |totalDifference = 0, spreading nothing");
        return;
    }

    // Find out the scaling factor required on totalDifference
    // to prevent moving the atom below the spreadThreshold
    if (h->getSTI() - totalDifference < spreadThreshold) {
        differenceScaling = (h->getSTI() - spreadThreshold) / totalDifference;
    }
   _log->fine("  +totaldifference %.2f, scaling %.2f", totalDifference,
            differenceScaling);

    for (linksVector_i = linksVector.begin();
            linksVector_i != linksVector.end(); ++linksVector_i) {
        double transferWeight;
        HandleSeq targets;
        HandleSeq::iterator t;
        Handle lh = *linksVector_i;
        TruthValuePtr linkTV = lh->getTruthValue();

        // For the case of an asymmetric link without this atom as a source
        if (!is_source(h, lh)) {
           _log->fine("Skipping link due to assymetric link without this atom as a source: " + h->toString());
            continue;
        }

        targets = lh->getOutgoingSet();
        transferWeight = linkTV->toFloat();

       _log->fine("  +Link %s", lh->toString().c_str() );
        //log->fine("    |weight %f, quanta %.2f, size %d",
       _log->fine("    |weight %f, size %d", \
                transferWeight, targets.size());

        for (t = targets.begin();
                t != targets.end();
                ++t)
        {
            Handle target_h = *t;
            AttentionValue::sti_t targetSTI;
            double transferAmount;

            // Then for each target of link except source...
            if (target_h == h) continue;

            targetSTI = target_h->getSTI();

            // calculate amount to transfer, based on difference and scaling
            if (lh->getType() == INVERSE_HEBBIAN_LINK) {
                // if the link is inverse, then scaling is unnecessary
                // note the negative sign
                transferAmount = -calcInverseDifference(sourceSTI,targetSTI, \
                        linkTV->toFloat());
            } else {
                // Check removing STI doesn't take node out of attentional
                // focus...
                transferAmount = calcInverseDifference(sourceSTI,targetSTI, \
                        linkTV->toFloat()) * differenceScaling;
            }

            h->setSTI(h->getSTI() - (AttentionValue::sti_t) transferAmount );
            target_h->setSTI(target_h->getSTI() + (AttentionValue::sti_t) transferAmount );
           _log->fine("    |%d sti from %s to %s", (int) transferAmount,
                    h->toString().c_str(), target_h->toString().c_str() );
        }
    }
}
