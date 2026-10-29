# Convenzioni per i commit

## 1. Scopo

Questo documento definisce le convenzioni da seguire nella creazione dei *commit*, con l'obiettivo di rendere la cronologia delle modifiche chiara, coerente e facilmente consultabile.

Le convenzioni si applicano a tutti i membri del team che contribuiscono al *repository*.

## 2. Struttura del messaggio

Ogni commit deve avere un messaggio breve e descrittivo, che riassuma la modifica introdotta.

Il messaggio deve seguire la struttura:

`<tipo>: <descrizione>`

La descrizione deve essere concisa, specifica e formulata in modo da identificare chiaramente lo scopo della modifica.

## 3. Tipologie di commit

Il tipo identifica la natura principale della modifica. Si adottano le seguenti tipologie:

- `docs`: aggiunta, modifica o rimozione di documentazione.
- `admin`: modifiche organizzative e amministrative, incluse le modifiche ai file relativi al *way of working*, la riorganizzazione delle directory e la gestione dei workflow.
- `website`: modifiche al sito web e ai relativi contenuti o stili.

Quando una modifica coinvolge più ambiti, scegliere il tipo che rappresenta meglio il suo obiettivo principale.

## 4. Regole di scrittura

I messaggi dei commit devono rispettare le seguenti convenzioni:

- Utilizzare l'italiano, salvo termini tecnici comunemente adottati in inglese.
- Iniziare la descrizione con una lettera minuscola.
- Utilizzare una forma verbale coerente e diretta, preferibilmente al participio passato.
- Non terminare il messaggio con un punto.
- Evitare descrizioni generiche come `aggiornamenti`, `modifiche varie` o `fix`.
- Evitare di includere nel messaggio dettagli non necessari o informazioni già ricavabili dal contesto.

È preferibile che ogni commit rappresenti una modifica logicamente coerente e circoscritta.

## 5. Riferimento alle issue

Quando il commit è associato a un'*issue*, si deve includere il riferimento nel messaggio, ad esempio:

`docs: aggiornate le convenzioni di formattazione (#24)`

Il riferimento deve corrispondere all'issue effettivamente associata alla modifica.

Quando una *Pull Request* risolve completamente un'issue, è possibile chiuderla automaticamente inserendo nella sua descrizione una keyword riconosciuta da GitHub, come `Closes`, seguita dall'identificativo dell'issue. Ad esempio:

`Redazione del verbale esterno. Closes #46`

## 6. Esempi

Esempi di messaggi conformi alle convenzioni:

- `docs: aggiornato il README del repository`
- `admin: modificato il workflow di compilazione LaTeX`
- `website: corretto il collegamento alla documentazione`

Esempi di messaggi da evitare:

- `aggiornamenti vari`
- `fix`
- `modifiche al sito.`
- `Docs: Update README`

## 7. Coerenza con il flusso di lavoro

I commit devono essere creati sul *branch* dedicato all'attività, seguendo la [strategia di branching](branching-strategy.md).

Prima di aprire una Pull Request, l'autore deve verificare che i commit siano comprensibili e coerenti con le modifiche proposte.

Quando necessario, i commit possono essere riorganizzati prima dell'integrazione, nel rispetto del flusso di revisione definito nella [policy di code review](code-review-policy.md).

L'integrazione nel branch `main` avviene secondo la [strategia di merge](branching-strategy.md) definita per il repository.

## 8. Revisione del documento

Le presenti convenzioni possono essere aggiornate tramite Pull Request quando emergono esigenze di uniformità o miglioramenti nel processo di gestione delle modifiche.