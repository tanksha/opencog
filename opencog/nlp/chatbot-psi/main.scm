(use-modules (opencog)
             (opencog nlp)
             (opencog nlp chatbot)
             (opencog nlp relex2logic)
             (opencog nlp sureal)
             (opencog nlp aiml)
             (opencog exec)
             (opencog openpsi))

; Load the utilities
(load "utils.scm")

; Load the states
(load "states.scm")

; Load the available contexts
(load "contexts.scm")
(load "pln-contexts.scm")

; Load the available actions
(load "actions.scm")
(load "external-sources.scm")
(load "random-sentence-generator.scm")
(load "pln-actions.scm")

; Load the psi-rules
(load "psi-rules.scm")
(load "pln-psi-rules.scm")

; Load r2l-rules
(load-r2l-rulebase)

; Load pln reasoner
(load "pln-reasoner.scm")

; Set relex-server-host
; (use-relex-server "localhost" 4444)
; (use-relex-server "relex" 4444)
(set-relex-server-host)

;-------------------------------------------------------------------------------
; Schema function for chatting

(define-public (chat utterance)
    (reset-all-chatbot-states)

    (let ((sent-node (car (nlp-parse utterance))))
        ; This is for keeping track of whether we have input that has not
        ; been handled
        (State input-utterance sent-node)

        ; These are for the contexts
        (State input-utterance-sentence sent-node)
        (State input-utterance-text (Node utterance))
        (State input-utterance-words (get-word-list sent-node))
    )

    *unspecified*
)

;-------------------------------------------------------------------------------
; Skip the demand (ConceptNode "OpenPsi: AIML chat demand"), a temp workaround

; Define the demand here to prevent error if this chatbot is loaded before
; loading the aiml psi-rules
(define aiml-chat-demand (psi-demand "AIML chat demand" .8))
(psi-demand-skip aiml-chat-demand)
(psi-reset-valid-demand-cache)

;-------------------------------------------------------------------------------
; Run OpenPsi if it's not already running

(if (not (psi-running?))
    (psi-run)
)
