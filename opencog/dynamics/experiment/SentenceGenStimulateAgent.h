/*
 * SentenceGenStimulateAgent.h
 *
 *  Created on: 10 Nov 2015
 *      Author: misgana
 */

#ifndef _SENTENCEGENAGENT_H_
#define _SENTENCEGENAGENT_H_

namespace opencog {
class Agent;
class SchemeEval;
class CogServer;
namespace ECANExperiment {

//extern std::vector<std::string> generated_sentences;
//extern std::vector<HandleSeq> sent_wordnodes;
//extern std::vector<HandleSeq> wordinstancenodes;
//
//extern UnorderedHandleSet hspecial_word_nodes;
//
//extern std::vector<std::string> special_words;
//extern std::vector<std::string> nspecial_words;
//extern int sent_size;
//extern int special_word_occurence_period;

/**
 * Generate Random sentence and stimulates them on some cognitive cycle interval.
 */
class SentenceGenStimulateAgent: public Agent {
private:
    UnorderedHandleSet _hword_wordInstance_nodes;
    SchemeEval* _scm_eval;
    AtomSpace& _as;

public:
    virtual ~ SentenceGenStimulateAgent();
    SentenceGenStimulateAgent(CogServer& cs);

    virtual const ClassInfo& classinfo() const;
    static const ClassInfo& info();
    void generate_stimuate_sentence(void);
    virtual void run();
};

}
}
#endif /* _SENTENCEGENAGENT_H_ */