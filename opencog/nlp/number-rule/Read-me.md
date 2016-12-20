# Number rule for OpenCog nlp pipeline

The need for this rule
- The relex and relex2logic results of sentences (with numeric values) parsed through OpenCog nlp pipeline is not recognizing a number as NumberNode

Given a SentenceNode sent, (num-rule sent) identifies any number (in string or numeric representation) 
from the sentence parsed through the nlp-parse, Create a NumberNode for those numbers
and Create a `ReferenceLink` to Word Instances reffering the numbers in a sentence.


num-rule.scm
 
- accepts a SentenceNode
- get words (in their order) of a sentence
- trim the instances and get the main word
- check for valid number string, and create a NumberNode 
- Finding the valid words, stores the corresponding WordNode index to create a ReferenceLink.

strtonum.scm

- convers strings like "two hundred and twenty five" into
numbers like 225.0 that can be used in numerical calculations.

Example:

- Start CogServer at port 17001
- Start relex server
- telnet localhost 17001
- Enter to the scheme shell 
	opencog> scm
- Load nlp modules	
	guile> (use-modules (opencog) (opencog nlp) (opencog nlp chatbot) (opencog nlp relex2logic))
- Parse the following sentence

  guile> (define sent (nlp-parse "The fridge should cost no more than fifteen thousand dollars"))
- Load the number rule procedures, apply it to sent and see the result

	guile> (load-scm-from-file ".../opencog/opencog/nlp/Number-rule/strtonum.scm")
  
	guile> (load-scm-from-file ".../opencog/opencog/nlp/Number-rule/strtonum.scm")
  
	guile> (num-rule sent)
  
	guile> (num-rule sent)
  
(ReferenceLink

   (NumberNode "15000.000000")
   
   (ListLink
   
      (WordInstanceNode "fifteen@0271e836-ea33-41d8-af43-973fdd6a230b")
      
      (WordInstanceNode "thousand@6e82f899-eabf-434b-b052-ee3a9751f6bb")
   )
)

The `ReferenceLink` will just link the word instances to the NumberNode.

- LIMITATIONS

Currently it can only be used to convert one number in a sentence. It can identify the numbers but give wrong answer. We are working on it.

guile> (define sent2 (nlp-parse "Two fridges should cost no more than fifteen thousand dollars"))

guile> (num-rule sent2)

(ReferenceLink

   (NumberNode "17000.000000")
   
   (ListLink
   
      (WordInstanceNode "two@3567bd97-9113-40f5-ac86-8f9c5fa8e835")
      (WordInstanceNode "fifteen@189dfe53-36a9-42cf-80f5-c39be3b21f0b")
      (WordInstanceNode "thousand@cec50370-94f1-4db5-87b7-1dfd002b6ddb")
   )
)








